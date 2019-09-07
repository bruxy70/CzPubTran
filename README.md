# CzPubTran
A Python package to rertrieve realtime information about public transit in CZ by calling CHAPS REST API.

Main purpose at the moment is to feed a sensor in Home-Assistant

# Install

pip install czpubtran

# Example usage

```
import asyncio
import logging
import aiohttp
from czpubtran.api import czpubtran

logging.basicConfig(level=logging.ERROR)

async def test():
    session=aiohttp.ClientSession(raise_for_status=True)
    bus = czpubtran(session,'')
    await bus.async_find_connection('Chyne, Haje','Ortenovo namesti','ABCz')
    print(f'Connection from {bus.origin} to {bus.destination} using timetable{bus.combination_id}')
    print('------------------------------------------------')
    print(f'Departure: {bus.departure} line {bus.line}')
    print(f'Duration: {bus.duration}')
    print('Connections:')
    for connection in bus.connections:
        print(f"line {connection['line']} "
            f"at {connection['depTime']} "
            f"from {connection['depStation']} "
            f"-> {connection['arrStation']} "
            f"{connection['arrTime']} "
            f"(delay: {connection['delay']} min)")
    await session.close()

asyncio.run(test())```