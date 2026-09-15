from odoo import api, models


class MixinIntegrationConnected(models.AbstractModel):
    _name = "mixin.integration.connected"
    _description = "Record With Its Own Connection"

    def _integration_connection_service(self) -> tuple[str, str, str]:
        raise NotImplementedError(
            f"{self._name} names the service its connections belong to: "
            "(code, name, category)"
        )

    def _get_integration_connection(self):
        self.check_singleton()
        code, name, category = self._integration_connection_service()
        return self.env["integration.connection"]._for_record(
            self, code, name, category
        )

    @api.ondelete(at_uninstall=True)
    def _unlink_integration_connections(self) -> None:
        self.env["integration.connection"].sudo().with_context(
            active_test=False
        ).search([("res_model", "=", self._name), ("res_id", "in", self.ids)]).unlink()
