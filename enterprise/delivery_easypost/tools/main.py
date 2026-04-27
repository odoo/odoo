# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import lxml.html
import requests

EASYPOST_URL = "https://www.easypost.com/docs/api"

def _parse_html_list(root_html, class_to_match, code_carrier_name_map):
    object_by_carrier = {}
    for node in root_html.xpath("//div[starts-with(@class, 'tab-pane " + class_to_match + "')]"):
        # On easypost website if a tab have a tag <p> it contains the text
        # 'No predefined packages for x.' and the list containing product packageing is
        # empty
        object_nodes = node.xpath(".//ul/li")
        if not object_nodes:
            continue
        carrier_name = [name for name in node.get('class').split(' ') if class_to_match in name][0]
        # Replace carrier code by real name.
        carrier_name = code_carrier_name_map.get(carrier_name.replace(class_to_match, ''))
        object_by_carrier[carrier_name] = []
        for object_node in object_nodes:
            object_by_carrier[carrier_name].append(object_node.text_content())
    return object_by_carrier

def _get_package_type(html, code_carrier_name_map):
    """ return a dictionary {'carrier name': [stock package types]}"""
    return _parse_html_list(html, 'predefined-carrier-', code_carrier_name_map)

def _get_service_level(html, code_carrier_name_map):
    """ return a dictionary {'carrier name': [service levels]}"""
    return _parse_html_list(html, 'carrier-', code_carrier_name_map)

def _map_carrier_name(html):
    code_carrier_name_map = {}
    for node in html.xpath("//option[starts-with(@data-target, '.carrier-')]"):
        code_carrier_name_map[node.get('data-target').split('-')[1]] = node.text_content().strip()
    return code_carrier_name_map

def easypost_generate_file():
    response = requests.get(EASYPOST_URL)
    root_html = lxml.html.fromstring(response.text)
    # Easypost website match code with real carrier name,
    # example AGSystems is the code for Associated Global Systems.
    # with the parser we want to return a code with
    # {carrier name:  service name}
    code_carrier_name_map = _map_carrier_name(root_html)
    package_types_by_carriers = _get_package_type(root_html, code_carrier_name_map)
    services_by_carriers = _get_service_level(root_html, code_carrier_name_map)
    with open('package_types_by_carriers.json', 'w') as package_types_by_carriers_file:
        json.dump(package_types_by_carriers, package_types_by_carriers_file)
    with open('services_by_carriers.json', 'w') as services_by_carriers_file:
        json.dump(services_by_carriers, services_by_carriers_file)


if __name__ == '__main__':
    easypost_generate_file()
