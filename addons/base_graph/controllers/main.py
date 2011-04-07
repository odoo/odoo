import glob, os
from xml.etree import ElementTree
import math
import simplejson
import openerpweb
import time
import datetime
from base.controllers.main import Xml2Json


COLOR_PALETTE = ['#f57900', '#cc0000', '#d400a8', '#75507b', '#3465a4', '#73d216', '#c17d11', '#edd400',
                 '#fcaf3e', '#ef2929', '#ff00c9', '#ad7fa8', '#729fcf', '#8ae234', '#e9b96e', '#fce94f',
                 '#ff8e00', '#ff0000', '#b0008c', '#9000ff', '#0078ff', '#00ff00', '#e6ff00', '#ffff00',
                 '#905000', '#9b0000', '#840067', '#510090', '#0000c9', '#009b00', '#9abe00', '#ffc900', ]

_colorline = ['#%02x%02x%02x' % (25 + ((r + 10) % 11) * 23, 5 + ((g + 1) % 11) * 20, 25 + ((b + 4) % 11) * 23) for r in range(11) for g in range(11) for b in range(11) ]

def choice_colors(n):
        if n > len(COLOR_PALETTE):
            return _colorline[0:-1:len(_colorline) / (n + 1)]
        elif n:
            return COLOR_PALETTE[:n]
        return []

class GraphView(openerpweb.Controller):
    _cp_path = "/base_graph/graphview"

    date_start = None
    date_delay = None
    date_stop = None
    color_field = None

    day_length = 8
    fields = {}
    events = []
    calendar_fields = {}
    ids = []
    model = ''
    domain = []
    context = {}
    event_res = []
    colors = {}
    color_values = []

    @openerpweb.jsonrequest
    def load(self, req, model, view_id):
        m = req.session.model(model)
        r = m.fields_view_get(view_id, 'graph')
        r["arch"] = Xml2Json.convert_to_structure(r["arch"])
        return {'fields_view':r}

    @openerpweb.jsonrequest
    def get_events(self, req, **kw):
        self.model = kw['model']
        self.fields = kw['fields']

        model = req.session.model(self.model)
        event_ids = model.search([])
        return self.create_event(event_ids, model)

    def create_event(self, event_ids, model):
        self.events = model.read(event_ids, self.fields.values())
#        print "\n self.fields.values()++",self.fields.values()
#        print "\n self.events++++++++++++++++++++",self.events
#        result = [{'partner_id': 'China Export', 'amount_total': 3000.0}]


        return {'result': result}

