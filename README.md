# CzPubTran
A Python package to rertrieve realtime information about public transit in CZ by calling CHAPS REST API.

Main purpose at the moment is to feed a sensor in Home-Assistant

# Install

pip install czpubtran

# Example usage

```
import asyncio
import aiohttp
from czpubtran.api import czpubtran

async def test():
    session=aiohttp.ClientSession(raise_for_status=True)
    bus = czpubtran(session,'')

    timetables = await bus.async_list_combination_ids()
    print("Listing available timetables (Combination IDs)")
    print(timetables)

    print('------------------------------------------------')

    await bus.async_find_connection('Namesti Republiky','Chodov','ABCz')
    print(f'First connection from {bus.origin} to {bus.destination} using timetable {bus.combination_id}:')
    print(f'Departure: {bus.departure} line {bus.line}')
    print(f'Duration: {bus.duration}')
    print('Connections:')
    for i,description in [(0,'1st connection'),(1,'2nd connection')]:
        print(f'{description}:')
        for detail in bus.connection_detail[i]:
            print(f"line {detail['line']} "
                f"at {detail['depTime']} "
                f"from {detail['depStation']} "
                f"-> {detail['arrStation']} "
                f"{detail['arrTime']} "
                f"(delay: {detail['delay']} min)")

    print('------------------------------------------------')

    await bus.async_find_connection('Namesti Republiky','Chodov','ABCz','23:00')
    print(f'Scheduled connection from {bus.origin} to {bus.destination} at {bus.start_time}:')
    print(f'Departure: {bus.departure} line {bus.line}')
    print(f'Duration: {bus.duration}')
    print('Connections:')
    for i,description in [(0,'1st connection'),(1,'2nd connection')]:
        print(f'{description}:')
        for detail in bus.connection_detail[i]:
            print(f"line {detail['line']} "
                f"at {detail['depTime']} "
                f"from {detail['depStation']} "
                f"-> {detail['arrStation']} "
                f"{detail['arrTime']} "
                f"(delay: {detail['delay']} min)")

    await session.close()

asyncio.run(test())```