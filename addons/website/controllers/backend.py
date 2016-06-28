# -*- coding: utf-8 -*-
from openerp import http
from openerp.http import request
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta
from math import floor
import time
import operator

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT


class WebsiteBackend(http.Controller):

    @http.route('/website/fetch_dashboard_data', type="json", auth='user')
    def fetch_dashboard_data(self, date_from, date_to):

        params = request.env['ir.config_parameter']
        ga_client_id = params.get_param('google_management_client_id', default='')

        return {
            'currency': request.env.user.company_id.currency_id.id,
            'dashboards': {
                'visits': {
                    'ga_client_id': ga_client_id,
                }
            }
        }
