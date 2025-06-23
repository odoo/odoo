from odoo.exceptions import ValidationError
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountReconcileModel(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reco_model_obj = cls.env['account.reconcile.model']
        cls.company_id = cls.env.company.id

    def test_unique_match_label_param(self):
        vals = {
            'name': 'Test Reco Model',
            'company_id': self.company_id,
        }

        self.reco_model_obj.create(vals)
        # creation for same model name without any matching param should trigger ValidationError
        with self.assertRaises(ValidationError):
            self.reco_model_obj.create(vals)

        vals.update(
            match_label='contains',
            match_label_param='Test label param',
        )
        self.reco_model_obj.create(vals)
        # creation for same model configuration should trigger ValidationError
        with self.assertRaises(ValidationError):
            self.reco_model_obj.create(vals)

        vals.update(
            name='test reco model',
            match_label_param='test label param',
        )
        # for reco model name case-sensitivity is not considered unique
        # with match_label other then regex case-sensitivity is not considered unique for match_label_param
        with self.assertRaises(ValidationError):
            self.reco_model_obj.create(vals)

        # creation with different match_label_param should not conflict
        vals.update(match_label_param='Test label param 1')
        self.reco_model_obj.create(vals)

        # creation with same configuration but different company_id should not conflict
        other_company = self.setup_other_company()['company']
        vals.update(company_id=other_company.id)
        self.reco_model_obj.create(vals)

        vals.update(
            match_label='match_regex',
            match_label_param='^Test.*',
        )
        self.reco_model_obj.create(vals)
        # creation with identical regex should trigger ValidationError
        with self.assertRaises(ValidationError):
            self.reco_model_obj.create(vals)
        # with regex case-sensitivity is considered unique for match_label_param
        vals.update(match_label_param='^test.*')
        self.reco_model_obj.create(vals)
