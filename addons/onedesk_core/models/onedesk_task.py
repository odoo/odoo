from odoo import models, fields, api

class OnedeskTask(models.Model):
    _name = 'onedesk.task'
    _description = 'Tâches du personnel'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'priority desc, date_start'

    # Informations de base
    name = fields.Char(string='Nom de la tâche', required=True, tracking=True)
    active = fields.Boolean(string='Actif', default=True)

    task_type = fields.Selection([
        ('checkin', 'Check-in'),
        ('checkout', 'Check-out'),
        ('menage', 'Ménage'),
        ('maintenance', 'Maintenance'),
        ('inspection', 'Inspection'),
        ('laundry', 'Linge'),
        ('supplies', 'Approvisionnement'),
        ('other', 'Autre')],
        string='Type de tâche', required=True, tracking=True)

    priority = fields.Selection([
        ('0', 'Basse'),
        ('1', 'Normale'),
        ('2', 'Haute'),
        ('3', 'Urgente')],
        string='Priorité', default='1', tracking=True)

    # Assignation
    assigned_to = fields.Many2one('res.users', string='Assigné à', tracking=True)
    team_id = fields.Many2one('res.partner', string='Équipe/Département')

    # Dates et durées
    date_start = fields.Datetime(string='Date début', required=True, tracking=True)
    date_end = fields.Datetime(string='Date fin estimée')
    date_completed = fields.Datetime(string='Date de complétion réelle')

    estimated_duration = fields.Float(string='Durée estimée (heures)', default=1.0)
    actual_duration = fields.Float(string='Durée réelle (heures)', compute='_compute_actual_duration', store=True)

    # Statut
    status = fields.Selection([
        ('todo', 'À faire'),
        ('in_progress', 'En cours'),
        ('done', 'Terminée'),
        ('cancelled', 'Annulée')],
        string='Statut', default='todo', tracking=True)

    # Relations
    reservation_id = fields.Many2one('onedesk.reservation', string='Réservation associée', ondelete='cascade')
    unit_id = fields.Many2one('onedesk.unit', string='Unité', related='reservation_id.unit_id', store=True)
    property_id = fields.Many2one('onedesk.property', string='Propriété', related='unit_id.property_id', store=True)

    # Instructions et notes
    description = fields.Html(string='Description')
    instructions = fields.Text(string='Instructions')
    notes = fields.Text(string='Notes internes')

    # Suivi
    checklist_items = fields.Text(string='Liste de contrôle')
    completion_notes = fields.Text(string='Notes de complétion')

    require_photo = fields.Boolean(string='Photo requise', default=False)
    completion_photo_ids = fields.Many2many('ir.attachment', 'task_photo_rel', 'task_id', 'attachment_id',
                                             string='Photos de complétion')

    # Récurrence
    is_recurring = fields.Boolean(string='Tâche récurrente', default=False)
    recurrence_interval = fields.Integer(string='Intervalle (jours)')

    # Coûts
    estimated_cost = fields.Float(string='Coût estimé')
    actual_cost = fields.Float(string='Coût réel')
    currency_id = fields.Many2one('res.currency', string='Devise',
                                   default=lambda self: self.env.company.currency_id)

    # Calendrier
    calendar_event_id = fields.Many2one('calendar.event', string="Événement calendrier")

    # Computed fields
    @api.depends('date_start', 'date_completed')
    def _compute_actual_duration(self):
        for record in self:
            if record.date_start and record.date_completed:
                delta = record.date_completed - record.date_start
                record.actual_duration = delta.total_seconds() / 3600.0  # Conversion en heures
            else:
                record.actual_duration = 0.0

    # Actions
    def action_start(self):
        self.write({'status': 'in_progress'})

    def action_complete(self):
        self.write({
            'status': 'done',
            'date_completed': fields.Datetime.now()
        })

    def action_cancel(self):
        self.write({'status': 'cancelled'})

    @api.model
    def create_task_from_reservation(self, reservation):
        """Créer automatiquement les tâches liées à une réservation"""
        tasks = []

        # Tâche Check-in
        tasks.append(self.create({
            'name': f"Check-in – {reservation.unit_id.name}",
            'task_type': 'checkin',
            'date_start': reservation.start_date,
            'date_end': reservation.start_date,  # même date pour check-in
            'reservation_id': reservation.id,
        }))

        # Tâche Ménage / Check-out
        tasks.append(self.create({
            'name': f"Ménage – {reservation.unit_id.name}",
            'task_type': 'menage',
            'date_start': reservation.end_date,
            'date_end': reservation.end_date,
            'reservation_id': reservation.id,
        }))

        return tasks

    @api.model
    def create(self, vals):
        task = super().create(vals)
        # Création automatique de l'événement calendrier
        event_vals = {
            'name': task.name,
            'start': task.date_start,
            'stop': task.date_end or task.date_start,
            'user_id': task.assigned_to.id if task.assigned_to else False,
            'description': f"Tâche: {task.name}\nType: {task.task_type}",
        }
        event = self.env['calendar.event'].create(event_vals)
        task.calendar_event_id = event.id
        return task

    def write(self, vals):
        res = super().write(vals)
        # Mise à jour automatique de l'événement calendrier
        for task in self:
            if task.calendar_event_id:
                update_vals = {}
                if 'name' in vals:
                    update_vals['name'] = vals['name']
                if 'date_start' in vals:
                    update_vals['start'] = vals['date_start']
                if 'date_end' in vals:
                    update_vals['stop'] = vals['date_end']
                if 'assigned_to' in vals:
                    update_vals['user_id'] = vals['assigned_to']
                if update_vals:
                    task.calendar_event_id.write(update_vals)
        return res


# Héritage du modèle réservation pour créer automatiquement les tâches
class OnedeskReservation(models.Model):
    _inherit = 'onedesk.reservation'

    @api.model
    def create(self, vals):
        reservation = super().create(vals)
        # Crée les tâches automatiquement
        self.env['onedesk.task'].create_task_from_reservation(reservation)
        return reservation
