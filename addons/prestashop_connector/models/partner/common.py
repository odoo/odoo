from ...backend import prestashop
from ...unit.import_synchronizer import PrestashopImportSynchronizer, import_batch

@prestashop
class ResPartnerRecordImport(PrestashopImportSynchronizer):
    _model_name = 'prestashop.res.partner'

    def _after_import(self, erp_id):
        binder = self.binder_for(self._model_name)
        ps_id = binder.to_backend(erp_id)
        import_batch.delay(
            self.session,
            'prestashop.address',
            self.backend_record.id,
            filters={'filter[id_customer]': '[%d]' % (ps_id)},
            priority=10,
        )