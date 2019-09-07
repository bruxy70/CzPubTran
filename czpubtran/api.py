"""czpubtran library
"""
import logging, json
from datetime import datetime, date, time, timedelta
import asyncio
import aiohttp
import async_timeout

HTTP_TIMEOUT = 5

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
    def __init__(self, session, user_id):
        """Setup of the czpubtran library"""
        self._user_id = user_id
        self._combination_ids = {}
        self._load_defaults()
        self._session = session
    
    def _load_defaults(self):
        self._origin = ''
        self._destination = ''
        self._departure = ''
        self._first_connection = ''
        self._combination_id = ''
        self._duration = ''
        self._connections = []

    async def async_find_connection(self,origin,destination,combination_id):
        """Find a connection from origin to destination. Return True if succesfull."""
        if not self._guid_exists(combination_id):
            try:
                with async_timeout.timeout(HTTP_TIMEOUT):            
                    if not await self._async_find_schedule_guid(combination_id):
                        return False
            except:
                raise ErrorGettingData('Failed to find timetable combination ID')
        self._origin = origin
        self._destination = destination
        self._combination_id = combination_id
        url_connection = f'https://ext.crws.cz/api/{self._guid(combination_id)}/connections'
        if self._user_id=='':
            payload= {'from':origin, 'to':destination}
        else:
            payload= {'from':origin, 'to':destination,'userId':self._user_id}
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
                raise ErrorGettingData(f'Did not find any connection from {entity._origin} to {entity._destination}')
            connection = connection_decoded["connInfo"]["connections"][0]
            _LOGGER.debug( f"(connection from {origin} to {destination}: found id {str(connection['id'])}")
            self._duration = connection["timeLength"]
            self._departure = connection["trains"][0]["trainData"]["route"][0]["depTime"]
            self._connections.clear()
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
                self._connections.append(c)
            if len(c)>0:
                self._first_connection = self._connections[0]["line"]
            return True
        except ErrorGettingData as e:
            self._load_defaults()
            _LOGGER.error( f'Error getting connection: {e.value}')
            return False
        except:
            self._load_defaults()
            _LOGGER.error( 'Exception reading connection data')
            return False

    def _guid_exists(self,combination_id):
        """Return False if Combination ID needs to be updated."""
        try:
            if combination_id in self._combination_ids:
                today=datetime.now().date()
                if self._combination_ids[combination_id]['validTo'] >= today:
                    return True
                else:
                    return False
            else:
                return False
        except:
            return False # Refresh data on Error

    def _guid(self,combination_id):
        if combination_id in self._combination_ids:
            return self._combination_ids[combination_id]['guid']
        else:
            _LOGGER.error(f'GUID for timetable combination ID {combination_id} not found!')
            return ''
    
    def _add_combination_id(self,combination_id,guid,valid_to):
        if combination_id not in self._combination_ids:
            self._combination_ids[combination_id]={}
        self._combination_ids[combination_id]['guid']=guid
        self._combination_ids[combination_id]['validTo']=valid_to

    async def _async_find_schedule_guid(self,combination_id):
        """Find guid of the schedule (Combination ID)"""
        if self._guid_exists(combination_id):
            return True
        _LOGGER.debug( f'Updating CombinationInfo guid {combination_id}')
        url_combination  = 'https://ext.crws.cz/api/'
        if self._user_id=="":
            payload = {}
        else:
            payload= {'userId':self._user_id}
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
            for combination in combination_decoded["data"]:
                if combination['id'] == combination_id:
                    self._add_combination_id(combination_id,combination["guid"],datetime.strptime(combination["ttValidTo"], "%d.%m.%Y").date())
                    _LOGGER.debug( f"found guid {combination['guid']} valid till {datetime.strptime(combination['ttValidTo'], '%d.%m.%Y').date()}")
                    return True
        except ErrorGettingData as e:
            _LOGGER.error( f'Error getting CombinatonInfo: {e.value}')
        except:
            _LOGGER.error( 'Exception reading guid data')
        return False

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
    def first_connection(self):
        return self._first_connection

    @property
    def duration(self):
        return self._duration

    @property
    def connections(self):
        return self._connections
