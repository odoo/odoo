from odoo import models


class MailThreadSubjectSuggest(models.AbstractModel):
    _inherit = 'mail.thread'
    _name = 'mail.thread.subject.suggested'
    _description = 'Thread with suggested subject'

    def _store_thread_fields(self, res, *, request_list):
        super()._store_thread_fields(res, request_list=request_list)
        if 'showSubjectInSmallComposer' in request_list:
            res.attr('showSubjectInSmallComposer', lambda _: True)
        if 'suggestedSubject' in request_list:
            res.attr('suggestedSubject', lambda t: t._message_get_suggested_subject())

    def _message_get_suggested_subject(self):
        return self._message_get_suggested_subject_batch()[self.id]

    def _message_get_suggested_subject_batch(self):
        suggested = {thread.id: thread._message_compute_subject() for thread in self}
        if messages := self._sort_suggested_messages(self.message_ids):
            for record in self:
                record_msg = next(
                    (msg for msg in messages if msg.res_id == record.id and msg.message_type in ('comment', 'email')),
                    self.env['mail.message']
                )
                if not record_msg:
                    continue
                if subject := record_msg.subject:
                    suggested[record.id] = subject
        return suggested
