from odoo import models, fields, api
from datetime import datetime, timedelta

class OnedeskDashboard(models.Model):
    _name = 'onedesk.dashboard'
    _description = 'Dashboard OneDesk'

    name = fields.Char(string='Nom', default='Dashboard')

    # Statistiques en temps réel
    total_properties = fields.Integer(string='Total propriétés', compute='_compute_stats')
    total_units = fields.Integer(string='Total unités', compute='_compute_stats')
    total_reservations = fields.Integer(string='Total réservations', compute='_compute_stats')
    active_reservations = fields.Integer(string='Réservations actives', compute='_compute_stats')

    # Revenus
    revenue_today = fields.Monetary(string='Revenus aujourd\'hui', compute='_compute_revenue', currency_field='currency_id')
    revenue_week = fields.Monetary(string='Revenus semaine', compute='_compute_revenue', currency_field='currency_id')
    revenue_month = fields.Monetary(string='Revenus mois', compute='_compute_revenue', currency_field='currency_id')
    revenue_year = fields.Monetary(string='Revenus année', compute='_compute_revenue', currency_field='currency_id')

    currency_id = fields.Many2one('res.currency', string='Devise',
                                   default=lambda self: self.env.company.currency_id)

    # Taux d'occupation
    occupancy_rate_today = fields.Float(string='Taux occupation aujourd\'hui', compute='_compute_occupancy')
    occupancy_rate_week = fields.Float(string='Taux occupation semaine', compute='_compute_occupancy')
    occupancy_rate_month = fields.Float(string='Taux occupation mois', compute='_compute_occupancy')

    # Check-ins/outs du jour
    checkins_today = fields.Integer(string='Check-ins aujourd\'hui', compute='_compute_daily_stats')
    checkouts_today = fields.Integer(string='Check-outs aujourd\'hui', compute='_compute_daily_stats')

    # Tâches
    tasks_pending = fields.Integer(string='Tâches en attente', compute='_compute_task_stats')
    tasks_in_progress = fields.Integer(string='Tâches en cours', compute='_compute_task_stats')
    tasks_overdue = fields.Integer(string='Tâches en retard', compute='_compute_task_stats')

    @api.depends()
    def _compute_stats(self):
        for record in self:
            record.total_properties = self.env['onedesk.property'].search_count([('active', '=', True)])
            record.total_units = self.env['onedesk.unit'].search_count([('active', '=', True)])
            record.total_reservations = self.env['onedesk.reservation'].search_count([])
            record.active_reservations = self.env['onedesk.reservation'].search_count([
                ('state', 'in', ['confirmed', 'checked_in']),
                ('start_date', '<=', fields.Datetime.now()),
                ('end_date', '>=', fields.Datetime.now())
            ])

    @api.depends()
    def _compute_revenue(self):
        for record in self:
            today = fields.Date.today()
            start_of_week = today - timedelta(days=today.weekday())
            start_of_month = today.replace(day=1)
            start_of_year = today.replace(month=1, day=1)

            # Revenus du jour
            record.revenue_today = sum(self.env['onedesk.reservation'].search([
                ('start_date', '>=', fields.Datetime.to_datetime(today)),
                ('start_date', '<', fields.Datetime.to_datetime(today + timedelta(days=1))),
                ('state', 'in', ['confirmed', 'checked_in', 'checked_out'])
            ]).mapped('total_price'))

            # Revenus de la semaine
            record.revenue_week = sum(self.env['onedesk.reservation'].search([
                ('start_date', '>=', fields.Datetime.to_datetime(start_of_week)),
                ('state', 'in', ['confirmed', 'checked_in', 'checked_out'])
            ]).mapped('total_price'))

            # Revenus du mois
            record.revenue_month = sum(self.env['onedesk.reservation'].search([
                ('start_date', '>=', fields.Datetime.to_datetime(start_of_month)),
                ('state', 'in', ['confirmed', 'checked_in', 'checked_out'])
            ]).mapped('total_price'))

            # Revenus de l'année
            record.revenue_year = sum(self.env['onedesk.reservation'].search([
                ('start_date', '>=', fields.Datetime.to_datetime(start_of_year)),
                ('state', 'in', ['confirmed', 'checked_in', 'checked_out'])
            ]).mapped('total_price'))

    @api.depends()
    def _compute_occupancy(self):
        for record in self:
            total_units = record.total_units
            if total_units == 0:
                record.occupancy_rate_today = 0.0
                record.occupancy_rate_week = 0.0
                record.occupancy_rate_month = 0.0
                continue

            today = fields.Date.today()

            # Occupation aujourd'hui
            occupied_today = self.env['onedesk.reservation'].search_count([
                ('start_date', '<=', fields.Datetime.now()),
                ('end_date', '>=', fields.Datetime.now()),
                ('state', 'in', ['confirmed', 'checked_in'])
            ])
            record.occupancy_rate_today = (occupied_today / total_units) * 100

            # Occupation semaine (moyenne)
            start_of_week = today - timedelta(days=today.weekday())
            nights_in_week = 7
            total_night_units = total_units * nights_in_week

            occupied_nights = 0
            for i in range(nights_in_week):
                date = start_of_week + timedelta(days=i)
                occupied_nights += self.env['onedesk.reservation'].search_count([
                    ('start_date', '<=', fields.Datetime.to_datetime(date)),
                    ('end_date', '>', fields.Datetime.to_datetime(date)),
                    ('state', 'in', ['confirmed', 'checked_in'])
                ])

            record.occupancy_rate_week = (occupied_nights / total_night_units) * 100 if total_night_units > 0 else 0.0

            # Occupation mois (moyenne)
            start_of_month = today.replace(day=1)
            next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
            days_in_month = (next_month - start_of_month).days
            total_night_units_month = total_units * days_in_month

            occupied_nights_month = 0
            for i in range(days_in_month):
                date = start_of_month + timedelta(days=i)
                occupied_nights_month += self.env['onedesk.reservation'].search_count([
                    ('start_date', '<=', fields.Datetime.to_datetime(date)),
                    ('end_date', '>', fields.Datetime.to_datetime(date)),
                    ('state', 'in', ['confirmed', 'checked_in'])
                ])

            record.occupancy_rate_month = (occupied_nights_month / total_night_units_month) * 100 if total_night_units_month > 0 else 0.0

    @api.depends()
    def _compute_daily_stats(self):
        for record in self:
            today = fields.Date.today()
            tomorrow = today + timedelta(days=1)

            # Check-ins du jour
            record.checkins_today = self.env['onedesk.reservation'].search_count([
                ('start_date', '>=', fields.Datetime.to_datetime(today)),
                ('start_date', '<', fields.Datetime.to_datetime(tomorrow)),
                ('state', 'in', ['confirmed', 'checked_in'])
            ])

            # Check-outs du jour
            record.checkouts_today = self.env['onedesk.reservation'].search_count([
                ('end_date', '>=', fields.Datetime.to_datetime(today)),
                ('end_date', '<', fields.Datetime.to_datetime(tomorrow)),
                ('state', 'in', ['confirmed', 'checked_in'])
            ])

    @api.depends()
    def _compute_task_stats(self):
        for record in self:
            record.tasks_pending = self.env['onedesk.task'].search_count([('status', '=', 'todo')])
            record.tasks_in_progress = self.env['onedesk.task'].search_count([('status', '=', 'in_progress')])

            # Tâches en retard
            record.tasks_overdue = self.env['onedesk.task'].search_count([
                ('status', 'in', ['todo', 'in_progress']),
                ('date_start', '<', fields.Datetime.now())
            ])

    def action_view_reservations(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Réservations',
            'res_model': 'onedesk.reservation',
            'view_mode': 'list,kanban,form,calendar',
            'target': 'current',
        }

    def action_view_tasks(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tâches',
            'res_model': 'onedesk.task',
            'view_mode': 'list,kanban,form',
            'target': 'current',
        }

    def action_view_properties(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Propriétés',
            'res_model': 'onedesk.property',
            'view_mode': 'list,kanban,form',
            'target': 'current',
        }
