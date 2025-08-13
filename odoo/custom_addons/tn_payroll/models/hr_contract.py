from odoo import models, fields, api

class Contract(models.Model):
    _inherit = 'hr.contract'

    # Champs CNSS
    cnss_employee_rate = fields.Float(string="Taux CNSS Employé (%)", default=9.18)
    cnss_employer_rate = fields.Float(string="Taux CNSS Employeur (%)", default=16.57)

    # Exonération IRPP
    irpp_exempt = fields.Boolean(string="Exonéré IRPP", default=False)

    # Type de contrat tunisien
    tunisian_contract_type = fields.Selection([
        ('cdi', 'CDI'),
        ('cdd', 'CDD'),
        ('stage', 'Stage'),
        ('autre', 'Autre'),
    ], string="Type de contrat (TN)", default='cdi')

    # Salaire
    type_de_salaire = fields.Selection([
        ('M', 'Salaire fixe mensuel'),
        ('H', 'Salaire horaire'),
    ], string="Type de salaire")

    # Catégorie professionnelle (obligatoire)
    professional_category = fields.Selection([
        ('a', 'Catégorie A'),
        ('b', 'Catégorie B'),
        ('c', 'Catégorie C'),
    ], string="Catégorie Professionnelle", required=True)

    # Mode de paiement calculé automatiquement
    modepai = fields.Char(string="Mode de paiement", compute='_compute_mode', store=True,required=True)

    # Ancienneté et salaire
    an = fields.Float(string="Ancienneté")
    salaire = fields.Float(string="Salaire")
    #niveau de cnss et irpp
    indemn_logement = fields.Float(string="Indemnité de logement (Cas isolement)")
    indemn_licenciement = fields.Float(string="Indemnité de licenciement")
    indemn_zone_geo = fields.Float(string="Indemnité de zone géographique")
    indemn_salaire_unique = fields.Float(string="Indemnité de salaire unique")
    indemn_mission = fields.Float(string="Indemnité de mission (frais)")
    indemn_scolarite = fields.Float(string="Indemnité de scolarité")
    indemn_evenement = fields.Float(string="Indemnité événement familial")
    indemn_representation = fields.Float(string="Indemnité représentative de frais")
    autres_indem_affranchies = fields.Float(string="Autres indemnités affranchies CNAS et IRG")
    # --- Primes et indemnités affranchies CNSS uniquement ---
    indemn_panier = fields.Float(string="Indemnité de panier")
    indemn_transport = fields.Float(string="Indemnité de transport")
    indemn_outillage = fields.Float(string="Indemnité d’outillage")
    indemn_salissure = fields.Float(string="Indemnité de salissure")
    indemn_froid = fields.Float(string="Indemnité de froid")
    indemn_risque = fields.Float(string="Indemnité de risque")
    indemn_difficultes = fields.Float(string="Indemnité de difficultés")
    indemn_astreinte = fields.Float(string="Indemnité d’astreinte")
    autres_indem_cnss = fields.Float(string="Autres indemnités affranchies CNSS")

    # Calcul automatique du mode de paiement
    @api.depends('type_de_salaire')
    def _compute_mode(self):
        for record in self:
            if record.type_de_salaire == 'M':
                record.modepai = "Mensuel"
            elif record.type_de_salaire == 'H':
                record.modepai = "Horaire"
            else:
                record.modepai = ""
