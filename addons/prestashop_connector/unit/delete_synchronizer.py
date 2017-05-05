# -*- coding: utf-8 -*-
from openerp.tools.translate import _
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.unit.synchronizer import Deleter
from ..connector import get_environment


class PrestashopDeleteSynchronizer(Deleter):
    """ Base deleter for Prestashop """

    def run(self, external_id):
        """ Run the synchronization, delete the record on Prestashop

        :param external_id: identifier of the record to delete
        """
        self.backend_adapter.delete(external_id)
        return _('Record %s deleted on Prestashop') % external_id


@job
def export_delete_record(session, model_name, backend_id, external_id):
    """ Delete a record on Prestashop """
    env = get_environment(session, model_name, backend_id)
    deleter = env.get_connector_unit(PrestashopDeleteSynchronizer)
    return deleter.run(external_id)
