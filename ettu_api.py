#!/usr/bin/env python
# pylint: disable=W0613, C0116

import requests
from lxml import html


def get_stations_by_first_letter(letter: str):
    response = requests.get("https://mobile.ettu.ru/stations/%s" % letter).text
    if not response:
        return {
            'error': True,
            'payload': None
        }

    result = {
        'error': False,
        'payload': list()
    }

    tree = html.fromstring(response)
    links = tree.xpath("//div")[0].xpath("./a[@href]")
    if len(links) == 0:
        return result

    result['payload'] = list(map(
        lambda link: {
            'name': link.text,
            'code': link.attrib['href'].rsplit('/', 1)[-1]
        },
        links
    ))

    return result


def get_car_timings_by_station_code(code: str):
    code = code.rsplit('/', 1)[-1]
    response = requests.get("https://mobile.ettu.ru/station/%s" % code).text
    if not response:
        return {
            'error': True,
            'payload': None
        }

    tree = html.fromstring(response)
    results_div = tree.xpath("//div")[0]

    station_name = results_div.xpath("./p")[0].text.strip()
    time = results_div.xpath("./p")[0].xpath("./b")[0].text.strip()

    result = {
        'error': False,
        'payload': {
            'station':  station_name,
            'time':     time,
            'cars':     None
        }
    }

    timing_divs = results_div.xpath("./div")

    cars_list = list()
    if len(timing_divs) > 1:
        timing_divs.pop(-1)
        for timing in timing_divs:
            divs = timing.xpath("./div")

            number = divs[0].xpath("./b")[0].text.strip()
            time = divs[1].text.strip()
            distance = divs[2].text.strip()

            cars_list.append({
                'number':   number,
                'time':     time,
                'distance': distance,
            })

    result['payload']['cars'] = cars_list

    return result



