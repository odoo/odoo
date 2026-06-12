# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.exceptions import AccessError


class PosLoadMixin(models.AbstractModel):
    _name = 'pos.load.mixin'
    _description = "PoS data loading mixin"

    @api.model
    def _load_pos_data_search_read(self, data, config):
        """ Search and return records to be loaded in the pos """
        if not config:
            raise ValueError("config must be provided to search for PoS data.")

        domain = self._server_date_to_domain(self._load_pos_data_domain(data, config))
        if domain is False:
            return []

        records = self.search(domain)
        return self._load_pos_data_read(records, config)

    @api.model
    def _load_pos_data_domain(self, data, config):
        """ Return the domain used to filter records """
        return []

    @api.model
    def _server_date_to_domain(self, domain):
        """ Optionally restrict the domain to records modified after the last server sync """
        if domain is False:
            return domain

        if last_server_date := self._last_server_date_to_load():
            domain = Domain.AND([domain, [('write_date', '>', last_server_date)]])

        return domain

    def _last_server_date_to_load(self):
        last_server_date = self.env.context.get('pos_last_server_date', False)
        limited_loading = self.env.context.get('pos_limited_loading', True)
        model_included = self._name not in ['pos.session', 'pos.config']
        return limited_loading and model_included and last_server_date

    @api.model
    def _load_pos_data_read(self, records, config):
        """ Read specific fields from the given records """
        if not config:
            raise ValueError("config must be provided to read PoS data.")

        fields = self._load_pos_data_fields(config)
        records = records._filtered_access("read").read(fields, load=False)
        return records or []

    def _unrelevant_records(self, config):
        unrelevant_record_ids = []
        for record in self:
            try:
                if not record.active:
                    unrelevant_record_ids.append(record.id)
            except AccessError:
                # If the user has no read access, consider the record as unrelevant
                unrelevant_record_ids.append(record.id)
        return unrelevant_record_ids

    @api.model
    def _load_pos_data_fields(self, config):
        """ Return the list of fields to be loaded """
        return []

    @api.model
    def _convert_pos_data_currency(self, records, config, price_field, currency_field):
        """ Convert ``price_field`` of each loaded record to the POS currency.

        ``records`` is the list of dicts returned by ``_load_pos_data_read`` and is
        updated in place. The source currency of each record is read from
        ``currency_field`` (an ``id``, as fields are read with ``load=False``); records
        already expressed in the ``config`` currency are left untouched.

        ``currency_field`` matters because a product stores its sale price and its cost
        in two potentially different currencies (``currency_id`` and
        ``cost_currency_id``): each price must be converted from its own currency.
        """
        records_by_currency = defaultdict(list)
        for record in records:
            currency_id = record[currency_field]
            if currency_id and currency_id != config.currency_id.id:
                records_by_currency[currency_id].append(record)

        date_today = fields.Date.today()
        for currency_id, currency_records in records_by_currency.items():
            currency = self.env['res.currency'].browse(currency_id)
            for record in currency_records:
                record[price_field] = currency._convert(
                    record[price_field], config.currency_id, self.env.company, date_today,
                )
