from odoo.tests import common

BTREE_INDEX_PY_DEFS = (True, '1', 'btree', 'btree_not_null')
# Ignore list of models and fields we don't want to index,
# usually because the table is known to always be small,
# or there is a custom index that covers this btree index
# A separate ignore list for models is provided to simplify maintenance.
BTREE_INDEX_IGNORE_MODELS = set()  # model._name
BTREE_INDEX_IGNORE_FIELDS = set()  # str(field)  (fully-qualified field name)

@common.tagged('post_install', '-at_install')
class TestOne2manyInverseIndexing(common.TransactionCase):

    def test_enforce_index_on_one2many_inverse(self):
        """Ensure btree indexes are enforced on the stored inverse fields of One2many relations."""
        def ignore(o2m_field, m2o_field):
            if not comodel._auto or comodel._abstract:
                return True  # tableless
            if comodel.is_transient():
                return True  # transient models shouldn't have a lot of records
            if not (m2o_field.store and m2o_field.column_type):
                return True  # the m2o isn't stored in database
            if o2m_field.comodel_name in BTREE_INDEX_IGNORE_MODELS:
                return True  # the o2m field's model is in the model ignore list
            if str(m2o_field) in BTREE_INDEX_IGNORE_FIELDS:
                return True  # the m2o field is in the field ignore list
            if m2o_field.index in BTREE_INDEX_PY_DEFS:
                return True  # the field is already indexed in the definition
            if all('test' in model_data.module
                   for model_data in self.env['ir.model.data'].search([('model', '=', comodel._name)])):
                return True  # skip model if it's exclusively used in testing modules
            return False

        fields_to_index = set()
        for model_name in self.env.registry:
            model = self.env[model_name]
            for field in model._fields.values():
                if field.type == 'one2many' and field.inverse_name:
                    comodel = self.env[field.comodel_name]
                    inverse_field = comodel._fields.get(field.inverse_name)
                    if inverse_field and not ignore(field, inverse_field):
                        fields_to_index.add(f"{inverse_field} (inverse of {field})")
        if fields_to_index:
            msg = ("The following fields should be indexed with a btree index,\n"
                   "as they are inverse of an One2many field:\n"
                   "- if the field is sparse -> 'btree_not_null'\n"
                   "- if the field is Required or low fraction of False/NULL values -> True or 'btree'\n"
                   "- if not sure -> 'btree_not_null': \n%s" % "\n".join(sorted(fields_to_index)))
            self.fail(msg)
