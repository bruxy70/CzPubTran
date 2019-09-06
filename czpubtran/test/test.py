import asyncio
import aiohttp
import logging
from czpubtran import (
    czpubtran
)

logging.basicConfig(level=logging.ERROR)

async def test():
    session=aiohttp.ClientSession(raise_for_status=True)
    a = czpubtran(session,'')
    await a.async_find_connection('Chyne, Haje','Ortenovo namesti','ABCz')
    print(f'Connection fom {a.origin} to {a.destination} using timetable {a.combination_id}')
    print('------------------------------------------------')
    print(f'Departure: {a.departure}')
    print(f'Duration: {a.duration}')
    connections_short=''
    connections_long=''
    delay=''
    long_delim=''
    for connection in a.connections:
        line=connection['line']
        depTime=connection['depTime']
        depStation=connection['depStation']
        arrTime=connection['arrTime']
        arrStation=connection['arrStation']
        if long_delim=='':
            connections_short=line
        else:
            connections_short=connections_short+"-"+depStation.replace(" (PZ)","")+"-"+line
        if connection['delay'] == '':
            connections_long=connections_long+long_delim+f'{line:<4} {depTime:<5} ({depStation}) -> {arrTime:<5} ({arrStation})'
        else:
            connections_long=connections_long+long_delim+f'{line:<4} {depTime:<5} ({depStation}) -> {arrTime:<5} ({arrStation})   !!! {connection["delay"]}min delayed'
            if delay=='':
                delay = f'line {line} - {connection["delay"]}min delay'
            else:
                delay = delay + f' | line {line} - {connection["delay"]}min delay'
        long_delim='\n'
    print(f'Short: {connections_short}')
    print(f'Long: {connections_long}')
    print(f'Delay: {delay}')
    await session.close()

asyncio.run(test())