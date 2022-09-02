# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""
The functions inside this file support the operation related to origin
In Origin we also save the model_id and model_name so that we can make
it a clickable link
Origin JSON format
[{
    name : 'PO0004',
    m_id : 4,
    m_name : 'purchase.order'
}]
"""

import json


def get_origins_set(origins):
    """This method will remove the duplicate origin
    origins should be a json array string"""
    u_names = dict()
    for origin in json.loads(origins):
        u_names[origin['name']] = origin
    return json.dumps(list(u_names.values()))

def union_origins(origins):
    """This method will get the union of origins
    origins should be a list of string each is an origin json"""
    try:
        return get_origins_set(json.dumps(sum([json.loads(origin) for origin in origins], [])))
    except (TypeError, json.JSONDecodeError):
        raise TypeError(f'Origins {origins} is not in json format. Use create_origin from odoo.tools.origin')

def create_origin(model=False, name=False):
    if not model:
        return json.dumps([{
            'name': name
        }])
    return json.dumps([{
            'm_name': model._name,
            'm_id': model._origin.id,
            'name': name or model.name
        }])

def get_names(origin):
    return [o['name'] for o in json.loads(origin)]

def get_names_str(origin):
    return ','.join(get_names(origin))

def name_in_origin(origin, name):
    try:
        return name in [o['name'] for o in json.loads(origin)]
    except (TypeError, json.JSONDecodeError):
        raise TypeError(f'Origin "{origin}" is not in json format. Use create_origin from odoo.tools.origin')
