from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import re

from odoo.tools.populate import compute


class Employee(models.Model):
    _inherit = 'hr.employee'

    cnss_number = fields.Char(string="CNSS Number",required=True)
    handicapped = fields.Integer("Handicapped")
    age = fields.Integer("Age", compute='_compute_age', store=True)
    avances_sur_salaire= fields.Integer("Avancessur salaire")
    autres_retenues = fields.Float("Autres retenues")
    mode = fields.Selection([
        ('M', 'Mensuel'),
        ('H', 'Horaire'),
    ], string="Mode (horaire ou Mensuel):")

    point = fields.Selection([
        ('pointeuse_current', 'Pointeuse mois en cours'),
        ('pointeuse_last', 'Pointeuse mois dernier'),
        ('systeme', 'Système'),
        ('manuel', 'Manuel'),
    ], string="Choisir les pointages à considérer:")
    heures_travaillees = fields.Integer(string="Heures travaillées durant le mois")
    jours_travailles = fields.Integer (string="Jours travaillés (calculé)",compute='_compute_heur',readonly=1,store=1)
#quantite pour gestion presence
    quantite = fields.Integer(string="Quantité")
    horaire_legal = fields.Integer(string="Horaire Légal"  )
    # quantite pour saisie des heures sup
    quantite25 = fields.Integer(string="Quantité 25%")
    quantite50 = fields.Integer(string="Quantité 50%")
    quantite75 = fields.Integer(string="Quantité 75%")
    quantite100 = fields.Integer(string="Quantité 100%")
    # quantite pour conge
    quantite1=fields.Integer(string="Nombre de mois à considérer pour le congé ")
    quantite2=fields.Integer(string="Jours de congés acquis par mois travaillé	 ")
    quantite3=fields.Integer(string="Cumul des congés	")
    quantite4=fields.Integer(string="Congé pris	")
    quantite5=fields.Integer(string="Congé restant")
    # quantite pour absence et maladie
    quantite6=fields.Integer(string="congé Maladie en heures")
    quantite7=fields.Integer(string="Congé Maladie en jours ")







    _sql_constraints = [
        ('cnss_number_unique', 'unique(cnss_number)', 'CNSS Number must be unique!'),
        ('cin_unique', 'unique(cin)', 'CIN must be unique!'),
    ]

    @api.depends('birthday')
    def _compute_age(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.birthday:
                birth_date = fields.Date.to_date(rec.birthday)
                delta = relativedelta(today, birth_date)
                rec.age = delta.years
            else:
                rec.age = 0

    @api.onchange('children')
    def _onchange_children(self):
        for rec in self:
            if rec.children == 0:
                rec.handicapped = 0  # reset if no children
            elif rec.handicapped > rec.children:
                # optionally cap silently:
                rec.handicapped = rec.children

    @api.constrains('children', 'handicapped')
    def _check_handicapped_le_children(self):
        for rec in self:
            if rec.children == 0 and rec.handicapped != 0:
                raise ValidationError("If there are no children, 'Handicapped' must be 0.")
            if rec.handicapped > rec.children:
                raise ValidationError("'Handicapped' cannot exceed number of children.")

    @api.constrains('identification_id')
    def _check_identification_id(self):
        for rec in self:
            if rec.identification_id:
                id_str = rec.identification_id.strip()
                if len(id_str) != 8:
                    raise ValidationError("Identification ID must be exactly 8 characters long.")
                if not id_str.isdigit():
                    raise ValidationError("Identification ID must contain only numbers.")
    @api.depends('heures_travaillees')
    def _compute_heur(self):
        for record in self:
            if record.heures_travaillees:
                record.jours_travailles=record.heures_travaillees//8
            else:
                record.jours_travailles=0.0
    @api.constrains('quantite25','quantite50','quantite75','quantite100')
    def _check_total_quantite(self):
        for record in self:
            total = record.quantite25 + record.quantite50 + record.quantite75 + record.quantite100
            if total > 20:
                raise ValidationError("Le total des quantités ne peut pas dépasser 20.")