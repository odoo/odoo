from odoo import api, models


class TestOrmDiscussion(models.Model):
    _inherit = 'test_orm.discussion'

    @api.onchange('name')
    def _onchange_name(self):
        # test onchange modifying one2many field values
        if self.env.context.get('generate_dummy_message') and self.name == '{generate_dummy_message}':
            # update body of existings messages and emails
            for message in self.messages:
                message.body = 'not last dummy message'
            for message in self.important_messages:
                message.body = 'not last dummy message'
            # add new dummy message
            message_vals = self.messages._add_missing_default_values({'body': 'dummy message', 'important': True})
            self.messages |= self.messages.new(message_vals)
            self.important_messages |= self.messages.new(message_vals)

    @api.onchange('moderator')
    def _onchange_moderator(self):
        self.participants |= self.moderator

    @api.onchange('messages')
    def _onchange_messages(self):
        self.message_concat = "\n".join(["%s:%s" % (m.name, m.body) for m in self.messages])


class TestOrmMulti(models.Model):
    _inherit = 'test_orm.multi'

    @api.onchange('name')
    def _onchange_name(self):
        for line in self.lines:
            line.name = self.name

    @api.onchange('partner')
    def _onchange_partner(self):
        for line in self.lines:
            line.partner = self.partner

    @api.onchange('tags')
    def _onchange_tags(self):
        for line in self.lines:
            line.tags |= self.tags


class TestOrmComputeOnchange(models.Model):
    _inherit = 'test_orm.compute.onchange'

    @api.onchange('foo')
    def _onchange_foo(self):
        self.count += 1


class TestOrmComputedModifier(models.Model):
    _inherit = 'test_orm.computed.modifier'

    @api.onchange('bar')
    def _onchange_moderator(self):
        self.sub_bar = self.bar


class TestOrmCompute_Editable(models.Model):
    _inherit = 'test_orm.compute_editable'

    @api.onchange('line_ids')
    def _onchange_line_ids(self):
        for line in self.line_ids:
            # even if 'same' is not in the view, it should be the same as 'value'
            line.count += line.same
