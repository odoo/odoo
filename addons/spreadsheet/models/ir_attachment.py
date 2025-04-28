import logging


from odoo import models, _
from odoo.exceptions import AccessError


_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _move_spreadsheet_files_to_db(self):
        """
        Moves all spreadsheet files from the filestore to the database.

        This method should be executed before sending the database to the upgrade platform.
        """
        if not self.env.is_admin():
            raise AccessError(_('Only administrators can execute this action.'))
        domain = self._get_spreadsheet_attachment_domain()
        attachments = self.search(domain)
        for attachment in attachments:
            attachment.db_datas = attachment.raw
        _logger.info("%s spreadsheet attachments moved to the database", len(attachments))

    def _move_spreadsheet_files_to_current_storage(self):
        """
        Moves all spreadsheet data from the database to the filestore.

        This method should be executed after restoring the database upgraded by the upgrade platform.
        """
        if not self.env.is_admin():
            raise AccessError(_('Only administrators can execute this action.'))
        if self._storage() == "db":
            return
        domain = self._get_spreadsheet_attachment_domain()
        attachments = self.search(domain)
        for attachment in attachments:
            attachment.raw = attachment.db_datas
        attachments.db_datas = False
        _logger.info("%s spreadsheet attachments moved from the database to the filestore", len(attachments))

    def _get_spreadsheet_attachment_domain(self):
        """
        Override this method to include attachments containing spreadsheet data
        to be be sent to the upgrade platform.
        """
        return []
