"""
czpubtran library
Calling CHAPS REST API to get information about public transport between two points
It uses two APIs - one to get guid of the timetable combination. Second (async_find_connection) to find the connection
The first one is internal and is called automatically if the guid is empty or expired
More info on https://crws.docs.apiary.io/
"""
import logging, json
from datetime import datetime, date, time, timedelta
import asyncio
import aiohttp
import async_timeout

HTTP_TIMEOUT = 10

_LOGGER = logging.getLogger(__name__)

class Guid_Not_Found(Exception):
    """Raised when we cannot find guid"""
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
    
class ErrorGettingData(Exception):
    """Raised when we cannot get data from API"""
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class czpubtran():
    
    """Constructor"""
    def __init__(self, session, user_id):
        """Setup of the czpubtran library"""
        self._user_id = user_id
        self._combination_ids = {}
        self._load_defaults()
        self._session = session
    
    def _load_defaults(self):
        """Erase the information"""
        self._origin = ''
        self._destination = ''
        self._departure = ''
        self._line = ''
        self._combination_id = ''
        self._duration = ''
        self._connection_detail = [[],[]]

    async def async_list_combination_ids(self):
        """List combination IDs available for the user account"""
        url_combination  = 'https://ext.crws.cz/api/'
        payload = {'userId':self._user_id} if self._user_id !="" else {}
        ids = []
        try:
            with async_timeout.timeout(HTTP_TIMEOUT):            
                combination_response = await self._session.get(url_combination,params=payload)
            if combination_response is None:
                raise ErrorGettingData('Response timeout reading timetable combination IDs')
            _LOGGER.debug( f'url - {combination_response.url}')
            if combination_response.status != 200:
                raise ErrorGettingData(f'Timetable combination IDs API returned response code {combination_response.status} ({await combination_response.text()})')
            combination_decoded = await combination_response.json()
            if combination_decoded is None:
                raise ErrorGettingData('Error passing the timetable combination IDs JSON response')
            if 'data' not in combination_decoded:
                raise ErrorGettingData('Timetable combination IDs API returned no data')
            for combination in combination_decoded["data"]:
                ids.append(combination['id'])
        except ErrorGettingData as e:
            _LOGGER.error( f'Error getting Combinaton IDs: {e.value}')
        except Exception as e:
            _LOGGER.error( f'Exception reading combination IDs: {e.args}')
        return ids
        
    def _get_connection(self,connection,index):
        """Decode and append connection detail"""
        for trains in connection["trains"]:
            c={}
            c['line']=str(trains["trainData"]["info"]["num1"])
            c['depTime']=trains["trainData"]["route"][0]["depTime"]
            c['depStation']=trains["trainData"]["route"][0]["station"]["name"]
            if "arrTime" in trains["trainData"]["route"][1]:
                c['arrTime']=trains["trainData"]["route"][1]["arrTime"]
            else:
                c['arrTime']=trains["trainData"]["route"][1]["depTime"]
            c['arrStation']=trains["trainData"]["route"][1]["station"]["name"]
            if 'delay' in trains and trains['delay'] >0:
                c['delay'] = trains["delay"]
            else:
                c['delay'] = ''
            self._connection_detail[index].append(c)

    async def async_find_connection(self,origin,destination,combination_id,t=None):
        """Find a connection from origin to destination. Return True if succesfull."""
        if not self._guid_exists(combination_id) and not await self._async_find_schedule_guid(combination_id):
            return False
        self._origin = origin
        self._destination = destination
        self._combination_id = combination_id
        url_connection = f'https://ext.crws.cz/api/{self._guid(combination_id)}/connections'
        payload={'from':origin, 'to':destination,'maxCount':'2'}
        if self._user_id!='': payload['userId']=self._user_id
        if t is not None: payload['dateTime']=t
        _LOGGER.debug( f'Checking connection from {origin} to {destination}')
        try:
            with async_timeout.timeout(HTTP_TIMEOUT):            
                connection_response = await self._session.get(url_connection,params=payload)
            if connection_response is None:
                raise ErrorGettingData('Response timeout')
            _LOGGER.debug( f'(url - {str(connection_response.url)}')
            if connection_response.status != 200:
                raise ErrorGettingData(f'API returned response code {connection_response.status} ({await connection_response.text()})')
            connection_decoded = await connection_response.json()
            if connection_decoded is None:
                raise ErrorGettingData('Error passing the JSON response')
            if "handle" not in connection_decoded:
                raise ErrorGettingData(f'Did not find any connection from {origin} to {destination}')
        except (asyncio.TimeoutError):
            _LOGGER.error( f'Response timeout getting public transport connection')
            return False
        except ErrorGettingData as e:
            self._load_defaults()
            _LOGGER.error( f'Error getting public transport connection data: {e.value}')
            return False
        except Exception as e:
            self._load_defaults()
            _LOGGER.error( f'Exception reading public transport connection data: {e.args}')
            return False
        try:
            self._connection_detail[0].clear()
            self._connection_detail[1].clear()
            if len(connection_decoded["connInfo"]["connections"])>=1:
                connection = connection_decoded["connInfo"]["connections"][0]
                _LOGGER.debug( f"(connection from {origin} to {destination}: found id {str(connection['id'])}")
                self._duration = connection["timeLength"]
                self._departure = connection["trains"][0]["trainData"]["route"][0]["depTime"]
                self._get_connection(connection,0)
                self._line = '' if len(self._connection_detail[0])==0 else self._connection_detail[0][0]["line"]
                if len(connection_decoded["connInfo"]["connections"])>=2: 
                    self._get_connection(connection_decoded["connInfo"]["connections"][1],1)
            return True
        except Exception as e:
            self._load_defaults()
            _LOGGER.error( f'Exception decoding received connection data: {e.args}')
            return False

    def _guid_exists(self,combination_id):
        """Return False if the timetable Combination ID needs to be updated."""
        try:
            if combination_id in self._combination_ids:
                today=datetime.now().date()
                return bool(self._combination_ids[combination_id]['dayRefreshed']==today and self._combination_ids[combination_id]['validTo'] >= today)
            else:
                return False
        except:
            return False # Refresh data on Error

    def _guid(self,combination_id):
        """Return guid of the timetable combination"""
        if combination_id in self._combination_ids:
            return self._combination_ids[combination_id]['guid']
        else:
            _LOGGER.error(f'GUID for timetable combination ID {combination_id} not found!')
            return ''
    
    def _add_combination_id(self,combination_id,guid,valid_to,day_refreshed):
        """Register newly found timetable Combination ID - so that it does not have to be obtained each time"""
        if combination_id not in self._combination_ids:
            self._combination_ids[combination_id]={}
        self._combination_ids[combination_id]['guid']=guid
        self._combination_ids[combination_id]['validTo']=valid_to
        self._combination_ids[combination_id]['dayRefreshed']=day_refreshed

    async def _async_find_schedule_guid(self,combination_id):
        """Find guid of the timetable Combination ID (combination ID can be found on the CHAPS API web site)"""
        if self._guid_exists(combination_id):
            return True
        _LOGGER.debug( f'Updating CombinationInfo guid {combination_id}')
        url_combination  = 'https://ext.crws.cz/api/'
        payload = {'userId':self._user_id} if self._user_id !="" else {}
        try:
            with async_timeout.timeout(HTTP_TIMEOUT):            
                combination_response = await self._session.get(url_combination,params=payload)
            if combination_response is None:
                raise ErrorGettingData('Response timeout reading timetable combination ID')
            _LOGGER.debug( f'url - {combination_response.url}')
            if combination_response.status != 200:
                raise ErrorGettingData(f'Timetable combination ID API returned response code {combination_response.status} ({await combination_response.text()})')
            combination_decoded = await combination_response.json()
            if combination_decoded is None:
                raise ErrorGettingData('Error passing the timetable combination ID JSON response')
            if 'data' not in combination_decoded:
                raise ErrorGettingData('Timetable combination ID API returned no data')
        except (asyncio.TimeoutError):
            _LOGGER.error( f'Response timeout reading timetable combination ID')
            return False
        except ErrorGettingData as e:
            _LOGGER.error( f'Error getting CombinatonInfo: {e.value}')
            return False
        except Exception as e:
            _LOGGER.error( f'Exception reading guid data: {e.args}')
            return False
        try:
            for combination in combination_decoded["data"]:
                if combination['id'] == combination_id:
                    today=datetime.now().date()
                    self._add_combination_id(combination_id,combination["guid"],datetime.strptime(combination["ttValidTo"], "%d.%m.%Y").date(),today)
                    _LOGGER.debug( f"found guid {combination['guid']} valid till {datetime.strptime(combination['ttValidTo'], '%d.%m.%Y').date()}")
                    return True
        except Exception as e:
            _LOGGER.error( f'Exception decoding guid data: {e.args}')
        return False

    """Properties"""
    @property
    def origin(self):
        return self._origin

    @property
    def destination(self):
        return self._destination

    @property
    def combination_id(self):
        return self._combination_id

    @property
    def departure(self):
        return self._departure

    @property
    def line(self):
        return self._line

    @property
    def duration(self):
        return self._duration

    @property
    def connection_detail(self):
        return self._connection_detail

    """For backward compatibility. To be depreciated"""
    @property
    def connection(self):
        return self._connection_detail[0]    