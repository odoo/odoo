# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo.tests import TransactionCase, tagged


@tagged("reference_cache")
class TestReferenceCache(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model = cls.env["test_new_api.mixed"]
        cls.records_a = cls.model.create(
            [
                {"reference": "%s,%d" % (reference._name, reference.id)}
                for reference in cls.env["test_new_api.model_a"].create([{"name": "hello_a"}] * 5)
            ]
        )
        cls.records_b = cls.model.create(
            [
                {"reference": "%s,%d" % (reference._name, reference.id)}
                for reference in cls.env["test_new_api.model_b"].create([{"name": "hello_b"}] * 5)
            ]
        )
        cls.records = cls.records_a | cls.records_b

    def test_reference_cache_models_mixed(self):
        """test_new_api.mixed records created:
        |- id -|------ reference ----------|
        |   1  | test_new_api.model_a,1    |
        |   2  | test_new_api.model_a,2    |
        |   3  | test_new_api.model_a,3    |
        |   4  | test_new_api.model_a,4    |
        |   5  | test_new_api.model_a,5    |
        |   6  | test_new_api.model_b,1    |
        |   7  | test_new_api.model_b,2    |
        |   8  | test_new_api.model_b,3    |
        |   9  | test_new_api.model_b,4    |
        |  10  | test_new_api.model_b,5    |

        Expected cache queries executed one for each model (3 queries):
         - record.reference:
            - SELECT * FROM test_new_api_mixed WHERE id IN (id1, id2, ..., id10)
         - record.reference.name (for first record.reference of model_a):
            - SELECT * FROM test_new_api_model_a WHERE id IN (a1, a2, ..., a5)
        - record.reference.name (for first occurrence of record.reference of model_b):
            - SELECT * FROM test_new_api_model_b WHERE id IN (b1, b2, ..., b5)

        Currently it is executing the following queries (11 queries):
         - record.reference:
            - SELECT * FROM test_new_api_mixed WHERE id IN (id1, id2, ..., id10)
        - record.reference.name:
            - SELECT * FROM test_new_api_model_a WHERE id IN (a1)
            - SELECT * FROM test_new_api_model_a WHERE id IN (a2)
            - ...
            - SELECT * FROM test_new_api_model_a WHERE id IN (a5)
            - SELECT * FROM test_new_api_model_b WHERE id IN (b1)
            - SELECT * FROM test_new_api_model_b WHERE id IN (b2)
            - ...
            - SELECT * FROM test_new_api_model_b WHERE id IN (b5)
        """

        self.env.cache.invalidate()
        with self.assertQueryCount(4):
            for record in self.records:
                record.reference.name

    def test_reference_cache_models_mixed_with_prefetch(self):
        """Same than original testing but using prefetch trick
        similar to https://github.com/odoo/odoo/blob/d0220457ad7ec725b/odoo/addons/base/models/ir_ui_menu.py#L113-L120
        in order to test it is running a few queries
        It is working well, however IMHO the API should do this trick instead for field.Reference
        """
        prefetch_ids = defaultdict(list)
        for reference in self.records.mapped("reference"):
            prefetch_ids[reference._name].append(reference.id)

        self.env.cache.invalidate()
        with self.assertQueryCount(4):
            for record in self.records:
                reference = record.reference
                reference = reference.with_prefetch(prefetch_ids[reference._name])
                reference.name
