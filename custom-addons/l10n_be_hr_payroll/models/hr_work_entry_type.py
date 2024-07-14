#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    meal_voucher = fields.Boolean(
        string="Meal Voucher", default=False,
        help="Work entries counts for meal vouchers")
    private_car = fields.Boolean(
        string="Private Car Reimbursement",
        help="Work entries counts for private car reimbursement")
    representation_fees = fields.Boolean(
        string="Representation Fees",
        help="Work entries counts for representation fees")
    # CODE - LABEL
    # 1   toutes les données relatives au temps de travail couvertes par une rémunération avec cotisations ONSS, à l'exception des vacances légales et complémentaires des ouvriers
    #    - travail effectif normal (également le travail adapté avec perte de salaire);
    #    - prestations supplémentaires sans repos compensatoire;
    #    - repos compensatoire autre que le repos compensatoire entreprise de construction et repos compensatoire dans le cadre d'une réduction de la durée du travail (voir cependant le code 20 pour le repos compensatoire dans le système du salaire horaire majoré);
    #    - incapacité de travail avec revenu garanti première semaine ou rémunération mensuelle garantie;
    #    - période de préavis ou période couverte par une indemnité de rupture ou par une indemnité de reclassement;
    #    - petits chômages;
    #    - raison impérieuse avec maintien du salaire;
    #    - absence couverte par une rémunération journalière garantie pour cause d'incapacité de travail;
    #    - rémunération journalière garantie pour une raison autre que l'incapacité de travail;
    #    - accident technique dans l'entreprise;
    #    - fermeture de l'entreprise à titre de protection de l'environnement;
    #    - jours fériés durant le contrat de travail, jours fériés après la fin du contrat de travail et jours de remplacement d'un jour férié;
    #    - autre absence avec maintien de la rémunération normale et cotisations ONSS (telle que l'absence autorisée avec maintien du salaire, congé politique,...)
    #    - vacances légales et complémentaires des employés.
    # 2   vacances légales pour ouvriers
    # 3   vacances complémentaires pour ouvriers
    # 4   absence premier jour par suite d'intempéries secteur de la construction (rémunération incomplète)
    # 5   congé-éducation payé ou congé formation flamand
    # 10  rémunération garantie deuxième semaine, jours fériés et jours de remplacement pendant la période de chômage temporaire, fonction de juge social
    # 11  incapacité de travail avec complément ou avance conformément à la CCT 12bis/13bis
    # 12  vacances en vertu d'une CCT rendue obligatoire ou repos compensatoire (construction, commerce de combustibles, industrie de l'habillement et de la confection, industrie et commerce du diamant, batellerie, culture et transformation primaire du lin et/ou du chanvre)
    # 13  promotion sociale
    # 14  jours de vacances supplémentaires en cas de début ou de reprise d'activité
    # 15  jours de vacances dont le paiement est inclus dans la rémunération flexi
    # 20  jours de repos compensatoire non rémunérés dans le cadre d'une diminution du temps de travail avec rémunération horaire majorée
    # 21  les jours de grève/lock-out
    # 22  mission syndicale
    # 23  jour de carence
    # 24  congé pour raisons impérieuses sans maintien de la rémunération - pour les gardien(ne)s d'enfants, jours de vacances non rémunérés (maximum 20) et jours fériés légaux lorsqu'il n'y a pas accueil d'enfants
    # 25  devoirs civiques sans maintien de la rémunération, mandat public
    # 26  obligations de milice
    # 30  toutes les données relatives au temps de travail pour lesquelles l'employeur ne paye pas de rémunération ni d'indemnité, à l'exception de celles reprises sous un autre code
    # 31  jours d'absence totale non rémunérée, assimilée à de l'activité de service, éventuellement fractionnables (ex.: congé pour des motifs impérieux d'ordre familial)
    # 32  jours d'absence totale non rémunérée avec position de non-activité, de disponibilité sans traitement d'attente ou de non-activité non rémunérée pour les militaires
    # 33  jours d'absence totale pour congé politique non rémunéré et assimilé à de l'activité de service
    # 41  jours d'absence totale rémunérée avec position de non-activité
    # 42  jours de disponibilité totale avec traitement d'attente et maintien du droit à l'avancement
    # 43  jours de retrait temporaire d'emploi pour motif de santé (militaires)
    # 50  maladie (maladie ou accident de droit commun)
    # 51  protection de la maternité (= mesure de protection de la maternité, repos de maternité ou congé de maternité converti en cas de décès ou d'hospitalisation de la mère) et pauses d'allaitement (CCT n° 80)
    # 52  congé de paternité ou de naissance, congé d'adoption et congé parental d'accueil (seulement les jours à charge du secteur “indemnités")
    # 53  maladie (congé prophylactique)
    # 60  accident du travail
    # 61  maladie professionnelle
    # 70  chômage temporaire autre que les codes 71, 72 et 77
    # 71  code spécifique chômage économique
    # 72  code spécifique chômage temporaire pour cause d'intempérie
    # 73  vacances jeunes et vacances seniors
    # 74  manque de prestations d'un gardien ou d'une gardienne d'enfants reconnu, dû à l'absence d'enfants normalement présents, mais qui sont absents pour des raisons indépendantes de la volonté du gardien ou de la gardienne d'enfants
    # 75  jours de soins d'accueil
    # 76  jours de suspension employés pour manque de travail
    # 77  Chômage temporaire pour force majeure Corona
    # 80  heures supplémentaires à ne pas récupérer et non soumises aux cotisations de sécurité sociale
    # 101 Jours de navigation des marins dans le secteur de la marine marchande, des travaux de dragage ou du remorquage maritime
    # 102 Jours de congé des marins dans le secteur de la marine marchande, des travaux de dragage ou du remorquage maritime
    # 110 Prestations d’un membre d'un parlement ou d'un gouvernement fédéral ou régional ou d’un mandataire local protégé ; jours couverts par une indemnité de sortie d'un membre d'un parlement, d'un gouvernement, d'une Députation permanente ou d'un collège provincial
    # 301 toutes les données relatives au temps de travail couvertes par une indemnité exonérée de cotisations de sécurité sociale, à l'exception de celles reprises sous un autre code

    dmfa_code = fields.Char(string="DMFA code", help="The DMFA Code will identify the work entry in DMFA report.")
    leave_right = fields.Boolean(
        string="Keep Time Off Right", default=False,
        help="Work entries counts for time off right for next year.")

    @api.model
    def get_work_entry_type_benefits(self):
        return ['meal_voucher', 'private_car', 'representation_fees']
