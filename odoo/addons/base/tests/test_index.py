from odoo.tests import common

BTREE_INDEX_PY_DEFS = (True, '1', 'btree', 'btree_not_null')
# Ignore list of models and fields we don't want to index,
# usually because the table is known to always be small,
# or there is a custom index that covers this btree index
# A separate ignore list for models is provided to simplify maintenance.
BTREE_INDEX_IGNORE_MODELS = set()  # model._name
BTREE_INDEX_IGNORE_FIELDS = {  # str(field)  (fully-qualified field name)
    'mail.message.res_id',                          # covered by _model_res_id_idx, should always be accessed via a domain adding the model
    'ir.attachment.res_id',                         # covered by _res_idx, should always be accessed via a domain adding the model
    'spreadsheet.revision.res_id',                  # covered by _res_model_res_id_idx, should be accessed via a domain adding the model
    'discuss.channel.member.channel_id',            # covered by first key of _seen_message_id_idx
    'documents.document.attachment_id',             # covered by _attachment_unique, which is enforced with an unique btree index
    'account.fiscal.position.account.position_id',  # covered by first key of _account_src_dest_uniq
    'mailing.subscription.contact_id',              # covered by first key of _unique_contact_list
    'iap.extracted.words.res_id',                   # covered by first key of _res_id_res_model_idx
    'knowledge.article.member.article_id',          # covered by first key of _unique_article_partner
    'slide.channel.forum_id',                       # covered by _forum_uniq
    'hr.appraisal.skill.appraisal_id',              # covered by first key of __unique_skill
}

@common.tagged('post_install', '-at_install')
class TestOne2manyInverseIndexing(common.TransactionCase):

    def test_enforce_index_on_one2many_inverse(self):
        """Ensure btree indexes are enforced on the stored inverse fields of One2many relations."""
        def ignore(o2m_field, m2o_field):
            ignore_tableless = not comodel._auto or comodel._abstract
            # transient models shouldn't have a lot of records
            ignore_transient = comodel.is_transient()
            ignore_non_stored = not(m2o_field.store and m2o_field.column_type)
            ignore_model = o2m_field.comodel_name in BTREE_INDEX_IGNORE_MODELS
            ignore_field = str(m2o_field) in BTREE_INDEX_IGNORE_FIELDS
            # skip model if it's exclusively used in testing modules
            ignore_test = all(
                'test' in model_data.module
                 for model_data in self.env['ir.model.data'].search([('model', '=', comodel._name)])
            )
            ignore_indexed = m2o_field.index in BTREE_INDEX_PY_DEFS
            return (ignore_tableless or ignore_transient or ignore_non_stored or
                    ignore_model or ignore_field or ignore_test or ignore_indexed)

        fields_to_index = set()
        for model_name in self.env.registry.models:
            model = self.env[model_name]
            for field in model._fields.values():
                if field.type == 'one2many' and field.inverse_name:
                    comodel = self.env[field.comodel_name]
                    inverse_field = comodel._fields.get(field.inverse_name)
                    if inverse_field and not ignore(field, inverse_field):
                        fields_to_index.add("%s (inverse of %s)" % (str(inverse_field), str(field)))
        if fields_to_index:
            msg = ("The following fields should be indexed with a btree index\n"
                   "- if the field is sparse -> 'btree_not_null'\n"
                   "- if the field is Required or low fraction of False/NULL values -> True\n"
                   "- if not sure -> 'btree_not_null': \n%s" % "\n".join(sorted(fields_to_index)))
            self.fail(msg)
