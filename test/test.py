import asyncio
import logging
import aiohttp
from datetime import datetime,time
from czpubtran.api import czpubtran

logging.basicConfig(level=logging.ERROR)

async def test():
    session=aiohttp.ClientSession(raise_for_status=True)
    bus = czpubtran(session,'')

    timetables = await bus.async_list_combination_ids()
    print("Listing available timetables (Combination IDs)")
    print(timetables)

    print('------------------------------------------------')

    await bus.async_find_connection('Chyne, Haje','Ortenovo namesti','ABCz')
    print(f'Connection from {bus.origin} to {bus.destination} using timetable {bus.combination_id}:')
    print(f'Departure: {bus.departure} line {bus.line}')
    print(f'Duration: {bus.duration}')
    print('Connections:')
    for i,description in [(1,'1st connection'),(2,'2nd connection')]:
        print(f'{description}:')
        for detail in bus.connection_detail[i]:
            print(f"line {detail['line']} "
                f"at {detail['depTime']} "
                f"from {detail['depStation']} "
                f"-> {detail['arrStation']} "
                f"{detail['arrTime']} "
                f"(delay: {detail['delay']} min)")

    t = time.strptime("23:00","%H:%M")
    await bus.async_find_connection('Ortenovo namesti','Chyne, Haje','ABCz',t)
    print(f'Connection from {bus.origin} to {bus.destination} at {}:')
    print(f'Departure: {bus.departure} line {bus.line}')
    print(f'Duration: {bus.duration}')


    await session.close()

asyncio.run(test())