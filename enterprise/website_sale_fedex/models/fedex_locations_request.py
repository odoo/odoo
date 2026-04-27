# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
from odoo.tools.zeep import Client, Settings, helpers
from odoo.tools.zeep.exceptions import Fault

from odoo.exceptions import UserError
from odoo.addons.delivery_fedex.models.fedex_request import remove_accents, FedexRequest, LogPlugin, STATECODE_REQUIRED_COUNTRIES
from odoo.models import _
from odoo.tools.misc import file_path


class AllStringEncoder(json.JSONEncoder):
    def default(self, obj):
        if not isinstance(obj, dict) and not isinstance(obj, list):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


class FEDEXLocationsRequest(FedexRequest):
    def __init__(self, debug_logger, request_type="locs", prod_environment=False):
        super(FEDEXLocationsRequest, self).__init__(debug_logger, request_type, prod_environment)
        wsdl_folder = 'prod' if prod_environment else 'test'
        wsdl_path = file_path(f'website_sale_fedex/api/{wsdl_folder}/LocationsService_v12.wsdl')
        self._start_locs_transaction(wsdl_path)

    def _start_locs_transaction(self, wsdl_path):
        settings = Settings(strict=False)
        self.client = Client('file:///%s' % wsdl_path.lstrip('/'), plugins=[LogPlugin(self.debug_logger)], settings=settings)
        self.factory = self.client.type_factory('ns0')
        self.VersionId = self.factory.VersionId()
        self.VersionId.ServiceId = 'locs'
        self.VersionId.Major = '12'
        self.VersionId.Intermediate = '0'
        self.VersionId.Minor = '0'

    def set_locs_details(self, carrier, ship_to):
        self.LocationsSearchCriterion = 'ADDRESS'

        self.Address = self.factory.Address()
        self.Address.City = remove_accents(ship_to.city)
        if ship_to.country_id.code in STATECODE_REQUIRED_COUNTRIES:
            self.Address.StateOrProvinceCode = ship_to.state_id.code
        else:
            self.Address.StateOrProvinceCode = ''
        self.Address.PostalCode = ship_to.zip
        self.Address.CountryCode = ship_to.country_id.code

        self.MultipleMatchesAction = 'RETURN_ALL'

        self.SortDetail = self.factory.LocationSortDetail()
        self.SortDetail.Criterion = 'DISTANCE'
        self.SortDetail.Order = 'LOWEST_TO_HIGHEST'

        self.Constraints = self.factory.SearchLocationConstraints()
        self.Constraints.RadiusDistance = self.factory.Distance()
        self.Constraints.RadiusDistance.Value = carrier.fedex_locations_radius_value
        self.Constraints.RadiusDistance.Units = carrier.fedex_locations_radius_unit.name.upper()

    def process_locs(self):
        _logger = logging.getLogger(__name__)
        try:
            self.response = self.client.service.searchLocations(
                WebAuthenticationDetail=self.WebAuthenticationDetail,
                ClientDetail=self.ClientDetail,
                TransactionDetail=self.TransactionDetail,
                Version=self.VersionId,
                LocationsSearchCriterion=self.LocationsSearchCriterion,
                Address=self.Address,
                MultipleMatchesAction=self.MultipleMatchesAction,
                SortDetail=self.SortDetail,
                Constraints=self.Constraints,
            )

            if self.response.HighestSeverity != 'ERROR' and self.response.HighestSeverity != 'FAILURE':
                response = self.response['AddressToLocationRelationships'][0]['DistanceAndLocationDetails']
                response = helpers.serialize_object(response, dict)
            else:
                raise UserError(
                    '\n'.join(
                        ("%s: %s" % (n.Code, n.Message))
                        for n in self.response.Notifications
                        if (n.Severity == 'ERROR' or n.Severity == 'FAILURE')
                    )
                )
            if any([n.Severity == 'WARNING' for n in self.response.Notifications]):
                _logger.warning(
                    '\n'.join(
                        ("%s: %s" % (n.Code, n.Message))
                        for n in self.response.Notifications
                        if n.Severity == 'WARNING'
                    )
                )

        except Fault as fault:
            raise UserError(_('There was an error retrieving Fedex localisations:\n%s', fault))
        except IOError:
            raise UserError(_('Fedex Server Not Found'))
        except ValueError:
            raise UserError(_('No Fedex pick-up points available for that shipping address'))
        return self._sanitize_response(response)

    def _sanitize_response(self, response):
        return json.loads(json.dumps(response, cls=AllStringEncoder))
