# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AIMessage(models.Model):
    """AI Conversation Message"""

    _name = 'ai.message'
    _description = 'AI Message'
    _order = 'create_date asc, id asc'

    conversation_id = fields.Many2one('ai.conversation', string='Conversation',
                                      required=True, ondelete='cascade', index=True)
    role = fields.Selection([
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
        ('tool', 'Tool'),
    ], string='Role', required=True, default='user')

    content = fields.Text(string='Content', required=True)
    metadata = fields.Text(string='Metadata',
                          help='JSON metadata (tool calls, usage stats, etc.)')

    is_error = fields.Boolean(string='Is Error', default=False,
                             help='Whether this message represents an error')

    create_date = fields.Datetime(string='Created On', readonly=True)

    def name_get(self):
        """Custom display name"""
        result = []
        for message in self:
            name = f'[{message.role.upper()}] {message.content[:50]}'
            if len(message.content) > 50:
                name += '...'
            result.append((message.id, name))
        return result
