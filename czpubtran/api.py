"""
czpubtran library
Calling CHAPS REST API to get information about public transport
between two points. It uses two APIs - one to get guid of the
timetable combination. Second (async_find_connection) to find the connection
The first one is internal and is called automatically
if the guid is empty or expired.
More info on https://crws.docs.apiary.io/
"""
import logging
import json
from datetime import datetime, date, time, timedelta
import asyncio
import aiohttp
import async_timeout

HTTP_TIMEOUT = 10

_LOGGER = logging.getLogger(__name__)


URL_CONNECTIONS = "https://main.crws.cz/api/{}/connections"
# URL_CONNECTIONS = "https://ext.crws.cz/api/{}/connections"
# URL_CONNECTIONS = "https://ext08.crws.cz/api/{}/connections"
# URL_CONNECTIONS = "https://ext14.crws.cz/api/{}/connections"
# URL_CONNECTIONS = "https://crws.timetable.cz/api/{}/connections"


class Guid_Not_Found(Exception):
    """Raised when we cannot find guid"""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def isTime(time_text):
    try:
        datetime.strptime(time_text, "%H:%M")
        return True
    except ValueError:
        return False


class ErrorGettingData(Exception):
    """Raised when we cannot get data from API"""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class czpubtran:

    """Constructor"""

    def __init__(self, session, user_id):
        """Setup of the czpubtran library"""
        self.__user_id = user_id
        self.__combination_ids = {}
        self.__load_defaults()
        self.__session = session

    def __load_defaults(self):
        """Erase the information"""
        self.__origin = ""
        self.__destination = ""
        self.__departure = ""
        self.__line = ""
        self.__combination_id = ""
        self.__duration = ""
        self.__start_time = None
        self.__connection_detail = [[], []]

    async def async_list_combination_ids(self):
        """List combination IDs available for the user account"""
        url_combination = "https://ext.crws.cz/api/"
        payload = {"userId": self.__user_id} if self.__user_id != "" else {}
        ids = []
        try:
            with async_timeout.timeout(HTTP_TIMEOUT):
                combination_response = await self.__session.get(
                    url_combination, params=payload
                )
            if combination_response is None:
                raise ErrorGettingData(
                    "Response timeout reading timetable combination IDs"
                )
            _LOGGER.debug(f"url - {combination_response.url}")
            if combination_response.status != 200:
                response_text = await combination_response.text()
                raise ErrorGettingData(
                    f"Timetable combination IDs API returned response code "
                    f"{combination_response.status} "
                    f"({response_text})"
                )
            combination_decoded = await combination_response.json()
            if combination_decoded is None:
                raise ErrorGettingData(
                    "Error passing the timetable combination IDs JSON response"
                )
            if "data" not in combination_decoded:
                raise ErrorGettingData("Timetable combination IDs API returned no data")
            for combination in combination_decoded["data"]:
                ids.append(combination["id"])
        except ErrorGettingData as e:
            _LOGGER.error(f"Error getting Combinaton IDs: {e.value}")
        except Exception as e:
            _LOGGER.error(f"Exception reading combination IDs: {e.args}")
        return ids

    def __get_connection(self, connection, index):
        """Decode and append connection detail"""
        for trains in connection["trains"]:
            c = {}
            c["line"] = str(trains["trainData"]["info"]["num1"])
            c["depTime"] = trains["trainData"]["route"][0]["depTime"]
            c["depStation"] = trains["trainData"]["route"][0]["station"]["name"]
            if "arrTime" in trains["trainData"]["route"][1]:
                c["arrTime"] = trains["trainData"]["route"][1]["arrTime"]
            else:
                c["arrTime"] = trains["trainData"]["route"][1]["depTime"]
            c["arrStation"] = trains["trainData"]["route"][1]["station"]["name"]
            if "delay" in trains and trains["delay"] > 0:
                c["delay"] = trains["delay"]
            else:
                c["delay"] = ""
            self.__connection_detail[index].append(c)

    async def async_find_connection(
        self, origin, destination, combination_id, start_time=None
    ):
        """Find a connection from origin to destination.
        Return True if succesfull."""
        if not self.__guid_exists(
            combination_id
        ) and not await self.__async_find_schedule_guid(combination_id):
            return False
        self.__origin = origin
        self.__destination = destination
        self.__combination_id = combination_id
        if start_time is None:
            self.__start_time = None
        else:
            self.__start_time = start_time
        url_connection = URL_CONNECTIONS.format(self.__guid(combination_id))
        payload = {"from": origin, "to": destination, "maxCount": "2"}
        if self.__user_id != "":
            payload["userId"] = self.__user_id
        if self.__start_time is not None:
            payload["dateTime"] = self.__start_time
        _LOGGER.debug(f"Checking connection from {origin} to {destination}")
        try:
            with async_timeout.timeout(HTTP_TIMEOUT):
                connection_response = await self.__session.get(
                    url_connection, params=payload
                )
            if connection_response is None:
                raise ErrorGettingData("Response timeout")
            _LOGGER.debug(f"(url - {str(connection_response.url)}")
            if connection_response.status == 500:
                response_text = await connection_response.text()
                if (
                    "exceptionCode" in response_text
                    and response_text["exceptionCode"] == 17
                ):
                    self.__combination_id = None
                    raise ErrorGettingData("Removed expired combination ID")
                if (
                    "exceptionCode" in response_text
                    and response_text["exceptionCode"] == 1023
                ):
                    _LOGGER.debug('Parallel API access is not allowed.')
                    return False
            if connection_response.status != 200:
                response_text = await connection_response.text()
                raise ErrorGettingData(
                    f"API returned response code "
                    f"{connection_response.status} "
                    f"({response_text})"
                )
            connection_decoded = await connection_response.json()
            if connection_decoded is None:
                raise ErrorGettingData("Error passing the JSON response")
            if "handle" not in connection_decoded:
                raise ErrorGettingData(
                    f"Did not find any connection " f"from {origin} to {destination}"
                )
        except (asyncio.TimeoutError):
            _LOGGER.error(f"Response timeout getting public transport connection")
            return False
        except ErrorGettingData as e:
            self.__load_defaults()
            _LOGGER.error(f"Error getting public transport connection data: {e.value}")
            return False
        except Exception as e:
            self.__load_defaults()
            _LOGGER.error(
                f"Exception reading public transport connection data: {e.args}"
            )
            return False
        try:
            self.__connection_detail[0].clear()
            self.__connection_detail[1].clear()
            if len(connection_decoded["connInfo"]["connections"]) >= 1:
                connection = connection_decoded["connInfo"]["connections"][0]
                _LOGGER.debug(
                    f"(connection from {origin} to {destination}: "
                    f"found id {str(connection['id'])}"
                )
                self.__duration = connection["timeLength"]
                self.__departure = connection["trains"][0]["trainData"]["route"][0][
                    "depTime"
                ]
                self.__get_connection(connection, 0)
                if len(self.__connection_detail[0]) == 0:
                    self.__line = ""
                else:
                    self.__line = self.__connection_detail[0][0]["line"]
                if len(connection_decoded["connInfo"]["connections"]) >= 2:
                    self.__get_connection(
                        connection_decoded["connInfo"]["connections"][1], 1
                    )
            return True
        except Exception as e:
            self.__load_defaults()
            _LOGGER.error(f"Exception decoding received connection data: {e.args}")
            return False

    def __guid_exists(self, combination_id):
        """Return False if the timetable Combination ID needs to be updated."""
        try:
            if combination_id in self.__combination_ids:
                today = datetime.now().date()
                return bool(
                    self.__combination_ids[combination_id]["dayRefreshed"] == today
                    and self.__combination_ids[combination_id]["validTo"] >= today
                )
            else:
                return False
        except Exception as e:
            return False  # Refresh data on Error

    def __guid(self, combination_id):
        """Return guid of the timetable combination"""
        if combination_id in self.__combination_ids:
            return self.__combination_ids[combination_id]["guid"]
        else:
            _LOGGER.error(
                f"GUID for timetable combination ID {combination_id} not found!"
            )
            return ""

    def __add_combination_id(self, combination_id, guid, valid_to, day_refreshed):
        """Register newly found timetable Combination ID
        So it does not have to be obtained each time"""
        if combination_id not in self.__combination_ids:
            self.__combination_ids[combination_id] = {}
        self.__combination_ids[combination_id]["guid"] = guid
        self.__combination_ids[combination_id]["validTo"] = valid_to
        self.__combination_ids[combination_id]["dayRefreshed"] = day_refreshed

    async def __async_find_schedule_guid(self, combination_id):
        """Find guid of the timetable Combination ID
        (combination ID can be found on the CHAPS API web site)"""
        if self.__guid_exists(combination_id):
            return True
        _LOGGER.debug(f"Updating CombinationInfo guid {combination_id}")
        url_combination = "https://ext.crws.cz/api/"
        payload = {"userId": self.__user_id} if self.__user_id != "" else {}
        try:
            with async_timeout.timeout(HTTP_TIMEOUT):
                combination_response = await self.__session.get(
                    url_combination, params=payload
                )
            if combination_response is None:
                raise ErrorGettingData(
                    "Response timeout reading timetable combination ID"
                )
            _LOGGER.debug(f"url - {combination_response.url}")
            if combination_response.status != 200:
                response_text = await combination_response.text()
                raise ErrorGettingData(
                    f"Timetable combination ID API returned response code "
                    f"{combination_response.status} ({response_text})"
                )
            combination_decoded = await combination_response.json()
            if combination_decoded is None:
                raise ErrorGettingData(
                    "Error passing the timetable combination ID JSON response"
                )
            if "data" not in combination_decoded:
                raise ErrorGettingData("Timetable combination ID API returned no data")
        except (asyncio.TimeoutError):
            _LOGGER.error(f"Response timeout reading timetable combination ID")
            return False
        except ErrorGettingData as e:
            _LOGGER.error(f"Error getting CombinatonInfo: {e.value}")
            return False
        except Exception as e:
            _LOGGER.error(f"Exception reading guid data: {e.args}")
            return False
        try:
            for combination in combination_decoded["data"]:
                if combination["id"] == combination_id:
                    today = datetime.now().date()
                    self.__add_combination_id(
                        combination_id,
                        combination["guid"],
                        datetime.strptime(combination["ttValidTo"], "%d.%m.%Y").date(),
                        today,
                    )
                    _LOGGER.debug(
                        f"found guid {combination['guid']} valid till "
                        f"{datetime.strptime(combination['ttValidTo'],'%d.%m.%Y').date()}"
                    )
                    return True
        except Exception as e:
            _LOGGER.error(f"Exception decoding guid data: {e.args}")
        return False

    """Properties"""

    @property
    def origin(self):
        return self.__origin

    @property
    def destination(self):
        return self.__destination

    @property
    def combination_id(self):
        return self.__combination_id

    @property
    def departure(self):
        return self.__departure

    @property
    def line(self):
        return self.__line

    @property
    def duration(self):
        return self.__duration

    @property
    def start_time(self):
        return self.__start_time

    @property
    def connection_detail(self):
        return self.__connection_detail

    """For backward compatibility. To be depreciated"""

    @property
    def connection(self):
        return self.__connection_detail[0]
