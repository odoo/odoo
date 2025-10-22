from odoo import api, fields, models, tools, _
from odoo.fields import Domain


class SlideChannelPartner(models.Model):
    _name = 'slide.channel.partner'
    _description = 'Channel / Partners (Members)'
    _table = 'slide_channel_partner'
    _rec_name = 'partner_id'

    active = fields.Boolean(string='Active', default=True)
    channel_id = fields.Many2one('slide.channel', string='Course', index=True, required=True, ondelete='cascade')
    member_status = fields.Selection([
        ('invited', 'Invite Sent'),
        ('joined', 'Joined'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Finished')],
        string='Attendee Status', readonly=True, required=True, default='joined')
    completion = fields.Integer('% Completed Contents', default=0, aggregator="avg")
    completed_slides_count = fields.Integer('# Completed Contents', default=0)
    partner_id = fields.Many2one('res.partner', index=True, required=True, ondelete='cascade')
    partner_email = fields.Char(related='partner_id.email', readonly=True)
    # channel-related information (for UX purpose)
    channel_user_id = fields.Many2one('res.users', string='Responsible', related='channel_id.user_id')
    channel_type = fields.Selection(related='channel_id.channel_type')
    channel_visibility = fields.Selection(related='channel_id.visibility')
    channel_enroll = fields.Selection(related='channel_id.enroll')
    channel_website_id = fields.Many2one('website', string='Website', related='channel_id.website_id')
    next_slide_id = fields.Many2one('slide.slide', string='Next Lesson', compute='_compute_next_slide_id')

    # Invitation
    invitation_link = fields.Char('Invitation Link', compute="_compute_invitation_link")
    last_invitation_date = fields.Datetime('Last Invitation Date')

    _channel_partner_uniq = models.Constraint(
        'unique(channel_id, partner_id)',
        'A partner membership to a channel must be unique!',
    )
    _check_completion = models.Constraint(
        'check(completion >= 0 and completion <= 100)',
        'The completion of a channel is a percentage and should be between 0% and 100.',
    )

    @api.depends('channel_id', 'partner_id')
    def _compute_invitation_link(self):
        ''' This sets the url used as hyperlink in the channel invitation email in template mail_notification_channel_invite.
        The partner_id is given in the url, as well as a hash based on the partner and channel id. '''
        for record in self:
            invitation_hash = record._get_invitation_hash()
            record.invitation_link = f'{record.channel_id.get_base_url()}/slides/{record.channel_id.id}/invite?invite_partner_id={record.partner_id.id}&invite_hash={invitation_hash}'

    def _compute_next_slide_id(self):
        if not self.ids:
            self.next_slide_id = False
            return
        self.env['slide.channel.partner'].flush_model()
        self.env['slide.slide'].flush_model()
        self.env['slide.slide.partner'].flush_model()
        query = """
            SELECT DISTINCT ON (SCP.id)
                SCP.id AS id,
                SS.id AS slide_id
            FROM slide_channel_partner SCP
            JOIN slide_slide SS
                ON SS.channel_id = SCP.channel_id
                AND SS.is_published = TRUE
                AND SS.active = TRUE
                AND SS.is_category = FALSE
                AND NOT EXISTS (
                    SELECT 1
                      FROM slide_slide_partner
                     WHERE slide_id = SS.id
                       AND partner_id = SCP.partner_id
                       AND completed = TRUE
                )
            WHERE SCP.id IN %s
            ORDER BY SCP.id, SS.sequence, SS.id
        """
        self.env.cr.execute(query, [tuple(self.ids)])
        next_slide_per_membership = {
            line['id']: line['slide_id']
            for line in self.env.cr.dictfetchall()
        }

        for membership in self:
            membership.next_slide_id = next_slide_per_membership.get(membership.id, False)

    def _recompute_completion(self):
        """ This method computes the completion and member_status of attendees that are neither
            'invited' nor 'completed'. Indeed, once completed, membership should remain so.
            We do not do any update on the 'invited' records.
            One should first set member_status to 'joined' before recomputing those values
            when enrolling an invited or archived attendee.
            It takes into account the previous completion value to add or remove karma for
            completing the course to the attendee (see _post_completion_update_hook)
        """
        read_group_res = self.env['slide.slide.partner'].sudo()._read_group(
            ['&', '&', ('channel_id', 'in', self.mapped('channel_id').ids),
             ('partner_id', 'in', self.mapped('partner_id').ids),
             ('completed', '=', True),
             ('slide_id.is_published', '=', True),
             ('slide_id.active', '=', True)],
            ['channel_id', 'partner_id'],
            aggregates=['__count'])
        mapped_data = {
            (channel.id, partner.id): count
            for channel, partner, count in read_group_res
        }

        completed_records = self.env['slide.channel.partner']
        uncompleted_records = self.env['slide.channel.partner']
        for record in self:
            if record.member_status in ('completed', 'invited'):
                continue
            was_finished = record.completion == 100
            record.completed_slides_count = mapped_data.get((record.channel_id.id, record.partner_id.id), 0)
            record.completion = round(100.0 * record.completed_slides_count / (record.channel_id.total_slides or 1))

            if not record.channel_id.active:
                continue
            elif not was_finished and record.channel_id.total_slides and record.completed_slides_count >= record.channel_id.total_slides:
                completed_records += record
            elif was_finished and record.completed_slides_count < record.channel_id.total_slides:
                uncompleted_records += record

            if record.completion == 100:
                record.member_status = 'completed'
            elif record.completion == 0:
                record.member_status = 'joined'
            else:
                record.member_status = 'ongoing'

        if completed_records:
            completed_records._post_completion_update_hook(completed=True)
            completed_records._send_completed_mail()

        if uncompleted_records:
            uncompleted_records._post_completion_update_hook(completed=False)

    def unlink(self):
        """
        Override unlink method :
        Remove attendee from a channel, then also remove slide.slide.partner related to.
        """
        if self:
            # find all slide link to the channel and the partner
            removed_slide_partner_domain = Domain.OR(
                Domain('partner_id', '=', channel_partner.partner_id.id)
                & Domain('slide_id', 'in', channel_partner.channel_id.slide_ids.ids)
                for channel_partner in self
            )
            self.env['slide.slide.partner'].search(removed_slide_partner_domain).unlink()
        return super().unlink()

    def _get_invitation_hash(self):
        """ Returns the invitation hash of the attendee, used to access courses as invited / joined. """
        self.ensure_one()
        token = (self.partner_id.id, self.channel_id.id)
        return tools.hmac(self.env(su=True), 'website_slides-channel-invite', token)

    def _post_completion_update_hook(self, completed=True):
        """ Post hook of _recompute_completion. Adds or removes
        karma given for completing the course.

        :param completed:
            True if course is completed.
            False if we remove an existing course completion.
        """
        for channel, memberships in self.grouped("channel_id").items():

            karma = channel.karma_gen_channel_finish
            if karma <= 0:
                continue

            karma_per_users = {}
            for user in memberships.sudo().partner_id.user_ids:
                karma_per_users[user] = {
                    'gain': karma if completed else karma * -1,
                    'source': channel,
                    'reason': _('Course Finished') if completed else _('Course Set Uncompleted'),
                }

            self.env['res.users']._add_karma_batch(karma_per_users)

    def _send_completed_mail(self):
        """ Send an email to the attendee when they have successfully completed a course. """
        template_to_records = dict()
        for record in self:
            template = record.channel_id.completed_template_id
            if template:
                template_to_records.setdefault(template, self.env['slide.channel.partner'])
                template_to_records[template] += record

        record_email_values = {}
        for template, records in template_to_records.items():
            record_values = template._generate_template(
                records.ids,
                ['attachment_ids',
                 'body_html',
                 'email_cc',
                 'email_from',
                 'email_to',
                 'mail_server_id',
                 'model',
                 'partner_to',
                 'reply_to',
                 'report_template_ids',
                 'res_id',
                 'scheduled_date',
                 'subject',
                ]
            )
            for res_id, values in record_values.items():
                # attachments specific not supported currently, only attachment_ids
                values.pop('attachments', False)
                values['body'] = values.get('body_html')  # keep body copy in chatter
                record_email_values[res_id] = values

        mail_mail_values = []
        for record in self:
            email_values = record_email_values.get(record.id)

            if not email_values or not email_values.get('partner_ids'):
                continue

            email_values.update(
                author_id=record.channel_id.user_id.partner_id.id or self.env.company.partner_id.id,
                auto_delete=True,
                recipient_ids=[(4, pid) for pid in email_values['partner_ids']],
            )
            email_values['body_html'] = template._render_encapsulate(
                'mail.mail_notification_light', email_values['body_html'],
                add_context={
                    'model_description': _('Completed Course')  # tde fixme: translate into partner lang
                },
                context_record=record.channel_id,
            )
            mail_mail_values.append(email_values)

        if mail_mail_values:
            self.env['mail.mail'].sudo().create(mail_mail_values)

    @api.autovacuum
    def _gc_slide_channel_partner(self):
        ''' The invitations of 'invited' attendees are only valid for 3 months. Remove outdated invitations
        with no completion. A missing last_invitation_date is also considered as expired.'''
        limit_dt = fields.Datetime.subtract(fields.Datetime.now(), months=3)
        expired_invitations = self.env['slide.channel.partner'].with_context(active_test=False).search([
            ('member_status', '=', 'invited'),
            ('completion', '=', 0),
            '|',
            ('last_invitation_date', '=', False),
            '&',
            ('last_invitation_date', '!=', False),
            ('last_invitation_date', '<', limit_dt),
        ])
        expired_invitations.unlink()
