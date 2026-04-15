# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models
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

        last_server_date = self.env.context.get('pos_last_server_date', False)
        limited_loading = self.env.context.get('pos_limited_loading', True)
        model_included = self._name not in ['pos.session', 'pos.config']

        if limited_loading and last_server_date and model_included:
            domain = Domain.AND([domain, [('write_date', '>', last_server_date)]])

        return domain

    @api.model
    def _load_pos_data_read(self, records, config):
        """ Read specific fields from the given records """
        if not config:
            raise ValueError("config must be provided to read PoS data.")

        import time
        import logging
        _logger = logging.getLogger(__name__)

        fields = self._load_pos_data_fields(config)

        # Allow each model to exclude slow computed fields from the ORM read.
        # These fields are then simulated efficiently in _process_pos_ui_data.
        fields_to_exclude = self._load_pos_data_fields_to_exclude(config, len(records))
        if fields_to_exclude:
            fields = [f for f in fields if f not in fields_to_exclude]

        start_read = time.time()
        read_records = records._filtered_access("read").read(fields, load=False)
        read_duration = time.time() - start_read

        start_process = time.time()
        if read_records:
            self._process_pos_ui_data(read_records, config)
        process_duration = time.time() - start_process

        _logger.info("PoS Load Detail: %s - read: %.2fs, process: %.2fs, count: %d",
                      self._name, read_duration, process_duration, len(read_records))

        return read_records or []

    @api.model
    def _load_pos_data_fields_to_exclude(self, config, record_count):
        """Return field names to exclude from ORM read for performance.

        Override this in each model to skip expensive computed/property fields.
        These fields should be simulated in _process_pos_ui_data instead.
        """
        return []

    @api.model
    def _process_pos_ui_data(self, records, config):
        """Post-process records before sending to the PoS client.

        Override this in each model to simulate excluded fields or add
        computed values. The base implementation converts binary image
        fields to booleans (presence checks) to avoid transferring large
        binary blobs to the frontend.
        """
        if not records:
            return

        for record in records:
            for img_field in ['image_128', 'image_256', 'image_512', 'image_1024', 'image_1920', 'image']:
                if img_field in record:
                    record[img_field] = bool(record[img_field])

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
