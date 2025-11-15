from odoo import models, fields, api

class OnedeskTask(models.Model):
    _name = 'onedesk.task'
    _description = 'Tâches du personnel'
    _rec_name = 'name'

    name = fields.Char(string='Nom de la tâche', required=True)
    task_type = fields.Selection([
        ('checkin', 'Check-in'),
        ('checkout', 'Check-out'),
        ('menage', 'Ménage'),
        ('maintenance', 'Maintenance')],
        string='Type de tâche', required=True)
    assigned_to = fields.Many2one('res.users', string='Assigné à')
    date_start = fields.Datetime(string='Date début', required=True)
    date_end = fields.Datetime(string='Date fin')
    status = fields.Selection([
        ('todo', 'À faire'),
        ('in_progress', 'En cours'),
        ('done', 'Terminée')],
        string='Statut', default='todo')
    reservation_id = fields.Many2one('onedesk.reservation', string='Réservation associée', ondelete='cascade')
    calendar_event_id = fields.Many2one('calendar.event', string="Événement calendrier")

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
