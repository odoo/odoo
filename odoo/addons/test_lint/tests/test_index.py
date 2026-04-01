from odoo.tests import common

BTREE_INDEX_PY_DEFS = (True, '1', 'btree', 'btree_not_null')
# Ignore list of models and fields we don't want to index,
# usually because the table is known to always be small,
# or there is a custom index that covers this btree index
# A separate ignore list for models is provided to simplify maintenance.
BTREE_INDEX_IGNORE_MODELS = {  # model._name
    'res.company',
    'stock.warehouse',
    'event.type',
    'event.type.mail',
    'event.type.ticket',
    'ir.sequence',
    'ir.sequence.date_range',
    'ir.module.module',
    'ir.module.module.dependency',
    'ir.module.module.exclusion',
}
BTREE_INDEX_IGNORE_FIELDS = {  # str(field)  (fully-qualified field name)
    'mail.message.res_id',                              # covered by _model_res_id_idx, should always be accessed via a domain adding the model
    'ir.attachment.res_id',                             # covered by _res_idx, should always be accessed via a domain adding the model
    'spreadsheet.revision.res_id',                      # covered by _res_model_res_id_idx, should be accessed via a domain adding the model
    'discuss.channel.member.channel_id',                # covered by first key of _seen_message_id_idx
    'discuss.channel.rtc.session.channel_member_id',    # covered by _channel_member_unique
    'documents.document.attachment_id',                 # covered by _attachment_unique, which is enforced with an unique btree index
    'account.fiscal.position.account.position_id',      # covered by first key of _account_src_dest_uniq
    'mailing.subscription.contact_id',                  # covered by first key of _unique_contact_list
    'knowledge.article.member.article_id',              # covered by first key of _unique_article_partner
    'slide.channel.forum_id',                           # covered by _forum_uniq
    'hr.appraisal.skill.appraisal_id',                  # covered by first key of __unique_skill
    'mail.presence.user_id',                            # covered by _user_unique
    'mail.presence.guest_id',                           # covered by _guest_unique
    'res.users.settings.user_id',                       # covered by _unique_user_id
    'project.collaborator.project_id',                  # covered by first key of _unique_collaborator
}

@common.tagged('post_install', '-at_install')
class TestIndex(common.TransactionCase):

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
            ir_model_id = self.env['ir.model']._get_id(comodel._name)
            modules = self.env['ir.model.data'].search_fetch([
                ('model', '=', 'ir.model'), ('res_id', '=', ir_model_id)
            ], ['module']).mapped('module')
            # ruff: noqa: SIM103
            if modules and all('test' in module for module in modules):
                return True  # skip model if it's in a test module
            return False

        fields_to_index = set()
        for model_name in self.env.registry:
            model = self.env[model_name]
            for field in model._fields.values():
                if field.type == 'one2many' and field.inverse_name:
                    comodel = self.env[field.comodel_name]
                    inverse_field = comodel._fields.get(field.inverse_name).base_field
                    if inverse_field and not ignore(field, inverse_field):
                        fields_to_index.add(f"{inverse_field} (inverse of {field})")
        if fields_to_index:
            msg = ("The following fields should be indexed with a btree index,\n"
                   "as they are inverse of an One2many field:\n"
                   "- if the field is sparse -> 'btree_not_null'\n"
                   "- if the field is Required or low fraction of False/NULL values -> True or 'btree'\n"
                   "- if not sure -> 'btree_not_null': \n%s" % "\n".join(sorted(fields_to_index)))
            self.fail(msg)
