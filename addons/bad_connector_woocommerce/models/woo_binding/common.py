from odoo import api, fields, models


class WooBinding(models.AbstractModel):
    """Abstract Model for the Bindings."""

    _name = "woo.binding"
    _inherit = "external.binding"
    _description = "WooCommerce Binding (abstract)"

    backend_id = fields.Many2one(
        comodel_name="woo.backend",
        string="Backend",
        required=True,
        ondelete="restrict",
    )
    external_id = fields.Char(string="ID on woo")
    woo_data = fields.Text()
    _sql_constraints = [
        (
            "unique_backend_external_id",
            "unique(backend_id, external_id)",
            "A binding with the same backend and external ID already exists!",
        ),
    ]

    @api.model
    def import_batch(
        self, backend, filters=None, force=False, job_options=None, **kwargs
    ):
        """Preparing Batch Import of"""
        if filters is None:
            filters = filters or {}
        with backend.work_on(self._name) as work:
            importer = work.component(usage="batch.importer")
            return importer.run(
                filters=filters, force=force, job_options=job_options, **kwargs
            )

    @api.model
    def import_record(
        self, backend, external_id, data=None, force=False, job_options=None, **kwargs
    ):
        """Import Record Of"""
        with backend.work_on(self._name) as work:
            importer = work.component(usage="record.importer")
            return importer.run(
                external_id=external_id, data=data, force=force, **kwargs
            )

    @api.model
    def export_batch(
        self, backend, fields=None, filters=None, job_options=None, **kwargs
    ):
        """Preparing Batch Export of"""
        if filters is None:
            filters = {}
        with backend.work_on(self._name) as work:
            exporter = work.component(usage="batch.exporter")
            return exporter.run(
                fields=fields, filters=filters, job_options=job_options, **kwargs
            )

    def export_record(self, backend, record, fields=None, job_options=None, **kwargs):
        """Export Record To"""
        record.ensure_one()
        with backend.work_on(self._name) as work:
            exporter = work.component(usage="record.exporter")
            return exporter.run(self, fields=fields, record=record, **kwargs)
