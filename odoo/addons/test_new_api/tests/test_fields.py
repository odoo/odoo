from odoo.tests import common
from odoo import fields
from odoo.exceptions import ValidationError

TEST_CASES = [
    {
        # no values
    }, {
        'basic': 'value',
    }, {
        'default': 'value',
    }, {
        'basic': 'value',
        'default': 'value',
    }
]

COMPUTED_VALUE= {
    'default': 'compute',
    'basic': 'basic',
}

DEFAULT_VALUE = {
    'default': 'default',
    'basic': False,
}

@common.tagged('prepostcomputes')
class TestPrePostComputes(common.TransactionCase):

    def test_pre_post_create_computes(self):
        Model = self.env["test_new_api.model_advanced_computes"]

        # Force computation on a new and assertRaises Error
        new_record = Model.new({
            'name1': 'Nathan',
            'name2': 'Algren',
            'title': 'Military Advisor',
        })
        with self.assertRaises(ValidationError):
            new_record.duplicates
        # Create two records and check duplicates are correctly assigned
        # If they were computed pre_create, duplicates fields would be empty.
        # Context key ensure the computes are all called during the create call.
        records = Model.with_context(creation=True).create([
            {
                'name1': 'Hans',
                'name2': 'zimmer',
                'title': 'Musical Composer'
            }, {
                'name1': 'hans',
                'name2': 'Zimmer',
                'title': 'Artist'
            }
        ])
        self.assertEqual(len(records), 2)
        self.assertEqual(records.duplicates, records)
        self.assertEqual(records[0].duplicates, records[1])
        self.assertEqual(records[1].duplicates, records[0])

        self.assertEqual(records[0].full_upper_name, records[1].full_upper_name)

    def test_x2m_precomputation(self):
        Model = self.env["test_new_api.model_advanced_computes"]
        recs = Model.with_context(creation=True).create([
            {
                'name1': 'Hans',
                'name2': 'zimmer',
                'title': 'Musical Composer',
                'child_ids': [(0,0,dict()), (0,0,dict())],
                'related_ids': [(0,0,dict()), (0,0,dict()), (0,0,dict()), (0,0,dict())]
            }, {
                'name1': 'hans',
                'name2': 'Zimmer',
                'title': 'Artist',
                'child_ids': [(0,0,dict())],
                'related_ids': [(0,0,dict()), (0,0,dict()), (0,0,dict())]
            }
        ])
        self.assertEqual(recs[0].related_value, 20.0)
        self.assertEqual(recs[0].children_value, 10.0)
        for display_info in recs[0].child_ids.mapped("display_info"):
            self.assertEqual(display_info, "Musical Composer\nBlabla")
        for display_info in recs[0].related_ids.mapped("display_info"):
            self.assertEqual(display_info, "\nBlabla")
