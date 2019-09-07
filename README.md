# CzPubTran
A Python package to rertrieve realtime information about public transit in CZ by calling CHAPS REST API.

Main purpose at the moment is to feed a sensor in Home-Assistant

# Install

pip install czpubtran

# Example usage

```
import asyncio
import aiohttp
import logging
from czpubtran.api import czpubtran

logging.basicConfig(level=logging.DEBUG)

async def test():
    session=aiohttp.ClientSession(raise_for_status=True)
    bus = czpubtran(session,'')
    await bus.async_find_connection('Cernosice, zel.zast.','Florenc','ABCz')
    print(f'Connection from {bus.origin} to {bus.destination} using timetable{bus.combination_id}')
    print('------------------------------------------------')
    print(f'Departure: {bus.departure}')
    print(f'Duration: {bus.duration}')
    print('Connections:')
    for connection in bus.connections:
        print(f"line {connection['line']} at {connection['depTime']} from {connection['depStation']} - > {connection['arrTime']} to {connection['arrStation']} (delay: {connection['delay']} min)")

asyncio.run(test())
```