# -*- coding: utf-8 -*-
import logging

from openerp.addons.connector.connector import ConnectorUnit
from openerp.addons.connector.unit.backend_adapter import BackendAdapter
from ..backend import prestashop

_logger = logging.getLogger(__name__)


class DirectBinder(ConnectorUnit):
    _model_name = None
    _erp_field = None
    _ps_field = None
    _copy_fields = []

    def _compare_function(ps_val, erp_val, ps_dict, erp_dict):
        raise NotImplementedError

    def run(self):
        _logger.debug(
            "[%s] Starting synchro between OERP and PS"
            % self.model._description
        )
        nr_ps_already_mapped = 0
        nr_ps_mapped = 0
        nr_ps_not_mapped = 0
        # Get all OERP obj
        sess = self.session
        erp_model_name = self.model._inherits.iterkeys().next()
        erp_rec_name = sess.pool[erp_model_name]._rec_name
        erp_ids = self.env[erp_model_name].search([])

        for erp_id in erp_ids:
            erp_list_dict = self.env[erp_model_name].browse(erp_id.id)
            adapter = self.unit_for(BackendAdapter)
            # Get the IDS from PS
            ps_ids = adapter.search()
            if not ps_ids:
                raise osv.except_osv(
                    _('Error :'),
                    _('Failed to query %s via PS webservice')
                    % adapter.prestashop_model
                )

            binder = self.binder_for()
            # Loop on all PS IDs
            for ps_id in ps_ids:
                # Check if the PS ID is already mapped to an OE ID
                erp_id = binder.to_openerp(ps_id)
                if erp_id:
                    # Do nothing for the PS IDs that are already mapped
                    _logger.debug(
                        "[%s] PS ID %s is already mapped to OERP ID %s"
                        % (self.model._description, ps_id, erp_id)
                    )
                    nr_ps_already_mapped += 1
                else:
                    # PS IDs not mapped => I try to match between the PS ID and
                    # the OE ID. First, I read field in PS
                    ps_dict = adapter.read(ps_id)
                    mapping_found = False
                    # Loop on OE IDs
                    for erp_dict in erp_list_dict:
                        # Search for a match
                        erp_val = erp_dict[self._erp_field]
                        ps_val = ps_dict[self._ps_field]
                        if self._compare_function(
                                ps_val,
                                erp_val,
                                ps_dict,
                                erp_dict):
                            # it matches, so I write the external ID
                            data = {
                                'openerp_id': erp_dict['id'],
                                'backend_id': self.backend_record.id,
                            }
                            for oe_field, ps_field in self._copy_fields:
                                data[oe_field] = erp_dict[ps_field]
                            ps_erp_id = self.env[self._model_name].with_context(sess.context).create(data)
                            binder.bind(ps_id, ps_erp_id)
                            _logger.debug(
                                "[%s] Mapping PS '%s' (%s) to OERP '%s' (%s)"
                                % (self.model._description,
                                   ps_dict['name'],  # not hardcode if needed
                                   ps_dict[self._ps_field],
                                   erp_dict[erp_rec_name],
                                   erp_dict[self._erp_field]))
                            nr_ps_mapped += 1
                            mapping_found = True
                            break
                    if not mapping_found:
                        # if it doesn't match, I just print a warning
                        _logger.warning(
                            "[%s] PS '%s' (%s) was not mapped to any OERP entry"
                            % (self.model._description,
                               ps_dict['name'],
                               ps_dict[self._ps_field]))

                        nr_ps_not_mapped += 1

        

        _logger.info(
            "[%s] Synchro between OERP and PS successfull"
            % self.model._description
        )
        _logger.info(
            "[%s] Number of PS entries already mapped = %s"
            % (self.model._description, nr_ps_already_mapped)
        )
        _logger.info(
            "[%s] Number of PS entries mapped = %s"
            % (self.model._description, nr_ps_mapped)
        )
        _logger.info(
            "[%s] Number of PS entries not mapped = %s"
            % (self.model._description, nr_ps_not_mapped)
        )

        return True

@prestashop
class LangDirectBinder(DirectBinder):
    _model_name = 'prestashop.res.lang'
    _erp_field = 'code'
    _ps_field = 'language_code'
    _copy_fields = [
        ('active', 'active'),
    ]

    def _compare_function(self, ps_val, erp_val, ps_dict, erp_dict):
        if len(erp_val) >= 2 and len(ps_val) >= 2 and \
                erp_val[0:2].lower() == ps_val[0:2].lower():
            return True
        return False


@prestashop
class CountryDirectBinder(DirectBinder):
    _model_name = 'prestashop.res.country'
    _erp_field = 'code'
    _ps_field = 'iso_code'

    def _compare_function(self, ps_val, erp_val, ps_dict, erp_dict):
        if len(erp_val) >= 2 and len(ps_val) >= 2 and \
                erp_val[0:2].lower() == ps_val[0:2].lower():
            return True
        return False


@prestashop
class ResCurrencyDirectBinder(DirectBinder):
    _model_name = 'prestashop.res.currency'
    _erp_field = 'name'
    _ps_field = 'iso_code'

    def _compare_function(self, ps_val, erp_val, ps_dict, erp_dict):
        if len(erp_val) == 3 and len(ps_val) == 3 and \
                erp_val[0:3].lower() == ps_val[0:3].lower():
            return True
        return False


@prestashop
class AccountTaxDirectBinder(DirectBinder):
    _model_name = 'prestashop.account.tax'
    _erp_field = 'amount'
    _ps_field = 'rate'

    def _compare_function(self, ps_val, erp_val, ps_dict, erp_dict):
        taxes_inclusion_test = self.backend_record.taxes_included and \
            erp_dict['price_include'] or not erp_dict['price_include']
        if taxes_inclusion_test and erp_dict['type_tax_use'] == 'sale' and \
                abs(erp_val*100 - float(ps_val)) < 0.01 and \
                self.backend_record.company_id.id == erp_dict['company_id'][0]:
            return True
        return False