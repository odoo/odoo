# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from collections import defaultdict
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from lxml import etree

from odoo import api, fields, models, _
from odoo.tools import date_utils
from odoo.tools.misc import file_path
from odoo.exceptions import ValidationError, UserError


def format_amount(amount, width=11, hundredth=True):
    """
    Fill a constant 11 characters string with 0
    """
    if hundredth:
        amount *= 100
    return str(int(amount)).zfill(width)

# TODO:
# - Anticipated Double Holiday Pay
# - Termination Fees (year >= 2014)

# Intellectuels ordinaire (Voir ANNEXE 2)
# Employés et apprentis de cette catégorie à partir de l'année où ils
# atteignent 19 ans: a) Employés de catégorie ordinaire. b) Sportifs
# rémunérés, limités à partir du 1er trimestre 2008 aux entraîneurs
# et arbitres de football, déclarés par des employeurs immatriculés
# sous les catégories 070 ou 076 c) Employés occasionnels déclarés
# sur base des rémunérations réelles par des employeurs
# immatriculés sous les catégories 116 et 117; d) officiers déclarés
# par des employeurs immatriculés sous les catégories 105, 205,
# 305 et 405.
# Présence autorisée pour le code travailleur (zone 00037) et le code
# travailleur cotisation (zone 00082)
WORKER_CODE = 495
STUDENT_CODE = 841

# ANNEXE 4: DEDUCTIONS (Only current ones)
# Current data of interest: Employment bonus (code 0001)
# +-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------+-------------------------------+---------------------------------------+-------------------------------------------------+---------------------------------------------------------------------+-------------------------------------------------------------------------+----------------+-------------+--------------------+------------------------------------+------------------------------------------------+
# | Code DMFA |                                                                                                                                                                       Libellé                                                                                                                                                                        | Réduction valide à partir du | Réduction valide jusqu'au | Réduction fédérale/ régionale | Réduction régionale - Région flamande | Réduction régionale - Région Bruxelles-Capitale | Réduction régionale - Région wallonne sans communes germano- phones | Réduction régionale - Région wallonne pour les communes germano- phones | Base de calcul |   Montant   | Date début droit à |               Niveau               | "Présence bloc ""Détail données déduc- tion""" |
# +-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------+-------------------------------+---------------------------------------+-------------------------------------------------+---------------------------------------------------------------------+-------------------------------------------------------------------------+----------------+-------------+--------------------+------------------------------------+------------------------------------------------+
# |      0001 | Réduction des cotisations personnelles pour les travailleurs ayant un bonus à l'emploi                                                                                                                                                                                                                                                               | 2000/1                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Interdit           | Ligne travailleur                  | Non                                            |
# |      0601 | Réduction des cotisations personnelles pour les travailleurs licenciés dans le cadre d'une restructuration                                                                                                                                                                                                                                           | 2007/1                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Obligatoire        | Ligne travailleur                  | Non                                            |
# |      1142 | Période transitoire : économie de réinsertion sociale conclue avant le 1.1.2004                                                                                                                                                                                                                                                                      | 2021/1                       | 9999/4                    | Régionale                     | Oui                                   | Non                                             | Oui                                                                 | Oui                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      1511 | Recherche scientifique                                                                                                                                                                                                                                                                                                                               | 1996/4                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Obligatoire    | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      2001 | Remboursement des frais de gestion S.S.A. - premier travailleur                                                                                                                                                                                                                                                                                      | 2004/1                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Interdit    | Interdit           | Ligne travailleur                  | Non                                            |
# |      3000 | Réduction structurelle                                                                                                                                                                                                                                                                                                                               | 2004/1                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      3240 | Economie d'insertion sociale  moins de 45 ans 312j/18m ou 156j/9m                                                                                                                                                                                                                                                                                    | 2021/1                       | 9999/4                    | Régionale                     | Oui                                   | Non                                             | Oui                                                                 | Non                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      3241 | Economie d'insertion sociale  moins de 45 ans  624j/36m ou 312j/18m                                                                                                                                                                                                                                                                                  | 2021/1                       | 9999/4                    | Régionale                     | Oui                                   | Non                                             | Oui                                                                 | Non                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      3250 | Economie d'insertion sociale  au moins 45 ans  156j/9m                                                                                                                                                                                                                                                                                               | 2021/1                       | 9999/4                    | Régionale                     | Oui                                   | Non                                             | Oui                                                                 | Non                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      3315 | Premiers engagements - premier travailleur - taxshift                                                                                                                                                                                                                                                                                                | 2016/1                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3324 | Premiers engagements - deuxième travailleur - taxshift - première période                                                                                                                                                                                                                                                                            | 2016/1                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3325 | Premiers engagements - deuxième travailleur - taxshift - deuxième période                                                                                                                                                                                                                                                                            | 2017/2                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3326 | Premiers engagements - deuxième travailleur - taxshift - troisième période                                                                                                                                                                                                                                                                           | 2018/2                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3333 | Premiers engagements - troisième travailleur - taxshift - première période                                                                                                                                                                                                                                                                           | 2016/1                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3334 | Premiers engagements - troisième travailleur - taxshift - deuxième période                                                                                                                                                                                                                                                                           | 2017/2                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3342 | Premiers engagements - quatrième travailleur - taxshift - première période                                                                                                                                                                                                                                                                           | 2016/1                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3343 | Premiers engagements - quatrième travailleur - taxshift - deuxième période                                                                                                                                                                                                                                                                           | 2017/2                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3352 | Premiers engagements - cinquième travailleur - taxshift - première période                                                                                                                                                                                                                                                                           | 2016/1                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3353 | Premiers engagements - cinquième travailleur - taxshift - deuxième période                                                                                                                                                                                                                                                                           | 2017/2                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3360 | Premiers engagements - sixième travailleur - taxshift - première période                                                                                                                                                                                                                                                                             | 2016/1                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3361 | Premiers engagements - sixième travailleur - taxshift - deuxième période                                                                                                                                                                                                                                                                             | 2017/2                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3500 | Réduction du temps de travail                                                                                                                                                                                                                                                                                                                        | 2004/1                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Oui                                            |
# |      3510 | Semaine de quatre jours                                                                                                                                                                                                                                                                                                                              | 2004/1                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3520 | Réduction du temps de travail et semaine de quatre jours                                                                                                                                                                                                                                                                                             | 2004/1                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Oui                                            |
# |      3700 | Réduction temporaire du temps de travail suite à la crise                                                                                                                                                                                                                                                                                            | 2020/3                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Oui                                            |
# |      3701 | Réduction temporaire du temps de travail suite au Brexit                                                                                                                                                                                                                                                                                             | 2021/1                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Oui                                            |
# |      3720 | Réduction temporaire du temps de travail combinée avec la semaine de quatre jours suite à la crise                                                                                                                                                                                                                                                   | 2020/3                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Oui                                            |
# |      3721 | Réduction temporaire du temps de travail combinée avec la semaine de quatre jours suite au Brexit                                                                                                                                                                                                                                                    | 2021/1                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Oui                                            |
# |      3800 | Tuteurs                                                                                                                                                                                                                                                                                                                                              | 2018/3                       | 9999/4                    | Régionale                     | Oui                                   | Non                                             | Non                                                                 | Oui                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      3900 | Travailleurs permanents dans l'horeca                                                                                                                                                                                                                                                                                                                | 2014/1                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      4000 | Contractuels subventionnés                                                                                                                                                                                                                                                                                                                           | 2018/1                       | 9999/4                    | Régionale                     | Oui                                   | Oui                                             | Oui                                                                 | Non                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      4001 | Contractuels subventionnés des administrations provinciales et locales                                                                                                                                                                                                                                                                               | 2022/1                       | 9999/4                    | Régionale                     | Non                                   | Oui                                             | Oui                                                                 | Non                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      4100 | Remplaçants de contractuels et de statutaires dans le secteur public                                                                                                                                                                                                                                                                                 | 2014/1                       | 9999/4                    | Fédérale                      | -                                     | -                                               | -                                                                   | -                                                                       | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      4200 | Personnel de maison                                                                                                                                                                                                                                                                                                                                  | 2017/3                       | 9999/4                    | Régionale                     | Oui                                   | Oui                                             | Non                                                                 | Oui                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      4300 | Artistes                                                                                                                                                                                                                                                                                                                                             | 2014/1                       | 9999/4                    | Régionale                     | Oui                                   | Oui                                             | Oui                                                                 | Oui                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      4400 | Gardiens et gardiennes d'enfants reconnus                                                                                                                                                                                                                                                                                                            | 2014/1                       | 9999/4                    | Régionale                     | Oui                                   | Oui                                             | Oui                                                                 | Oui                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      4500 | Travailleurs engagés dans le cadre de l'article 60 § 7 de la loi organique des CPAS du 08.07.1976                                                                                                                                                                                                                                                    | 2022/1                       | 9999/4                    | Régionale                     | Non                                   | Oui                                             | Oui                                                                 | Oui                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      6300 | Jeunes travailleurs peu qualifiés                                                                                                                                                                                                                                                                                                                    | 2016/3                       | 9999/4                    | Régionale                     | Oui                                   | Non                                             | Non                                                                 | Non                                                                     | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      6310 | Jeunes travailleurs apprentis                                                                                                                                                                                                                                                                                                                        | 2016/3                       | 9999/4                    | Régionale                     | Oui                                   | Non                                             | Non                                                                 | Non                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      6311 | Jeunes travailleurs  - en formation en alternance                                                                                                                                                                                                                                                                                                    | 2017/1                       | 9999/4                    | Régionale                     | Oui                                   | Non                                             | Non                                                                 | Non                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      6320 | Travailleurs âgés - en activité                                                                                                                                                                                                                                                                                                                      | 2016/3                       | 9999/4                    | Régionale                     | Oui                                   | Non                                             | Non                                                                 | Non                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      6321 | Travailleurs âgés - nouvel engagé                                                                                                                                                                                                                                                                                                                    | 2016/3                       | 9999/4                    | Régionale                     | Oui                                   | Non                                             | Non                                                                 | Non                                                                     | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      6330 | Réduction des cotisations patronales pour la marine marchande  le secteur du dragage et du remorquage                                                                                                                                                                                                                                                | 2018/1                       | 9999/4                    | Régionale                     | Oui                                   | Non                                             | Non                                                                 | Non                                                                     | Obligatoire    | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      7320 | Travailleurs âgés                                                                                                                                                                                                                                                                                                                                    | 2016/4                       | 9999/4                    | Régionale                     | Non                                   | Oui                                             | Non                                                                 | Non                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      8009 | Mesure transitoire - Programme de transition professionnelle moins de 25 ans moins qualifiés au moins 9 mois d'allocations ou moins de 45 ans au moins 12 mois d'allocation                                                                                                                                                                          | 2017/3                       | 9999/4                    | Régionale                     | Non                                   | Non                                             | Oui                                                                 | Non                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      8010 | Mesure transitoire - Programme de transition professionnelle moins de 45 ans  au moins 24 mois d'allocations                                                                                                                                                                                                                                         | 2017/3                       | 9999/4                    | Régionale                     | Non                                   | Non                                             | Oui                                                                 | Non                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      8011 | Mesure transitoire - Programme de transition professionnelle au moins 45 ans  au moins 12 mois d'allocations                                                                                                                                                                                                                                         | 2017/3                       | 9999/4                    | Régionale                     | Non                                   | Non                                             | Oui                                                                 | Non                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      8012 | Mesure transitoire - Programme de transition professionnelle au moins 45 ans  au moins 24 mois d'allocations                                                                                                                                                                                                                                         | 2017/3                       | 9999/4                    | Régionale                     | Non                                   | Non                                             | Oui                                                                 | Non                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      8320 | Travailleurs âgés                                                                                                                                                                                                                                                                                                                                    | 2017/3                       | 9999/4                    | Régionale                     | Non                                   | Non                                             | Oui                                                                 | Non                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      9002 | Mesure transitoire - Economie d'insertion sociale  au moins 45 ans  156j/9m                                                                                                                                                                                                                                                                          | 2019/1                       | 9999/4                    | Régionale                     | Non                                   | Non                                             | Non                                                                 | Oui                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      9300 | Travailleurs âgés                                                                                                                                                                                                                                                                                                                                    | 2019/1                       | 9999/4                    | Régionale                     | Non                                   | Non                                             | Non                                                                 | Oui                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      3203 | Mesure transitoire - Plan Activa - Demandeurs d'emploi de longue durée  moins de 45 ans  pendant 1560 jours dans une période de 90 mois  Codes ONEM : C7  C8  C28  C33 ou C39                                                                                                                                                                        | 2019/1                       | 2023/4                    | Régionale                     | Non                                   | Non                                             | Non                                                                 | Oui                                                                     | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3210 | Mesure transitoire - Plan Activa - Demandeurs d'emploi de longue durée  au moins de 45 ans  pendant 156 jours dans une période de 9 mois  Codes ONEM : D1  D13 ou D19                                                                                                                                                                                | 2019/1                       | 2023/4                    | Régionale                     | Non                                   | Non                                             | Non                                                                 | Oui                                                                     | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3211 | Mesure transitoire - Plan Activa - Demandeurs d'emploi de longue durée  au moins de 45 ans  pendant 312 jours dans une période de 18 mois  ou pendant 468 jours dans une période de 27 mois  Codes ONEM : D3  D4  D5  D6  D14  D15  D16  D17  D20 ou D21                                                                                             | 2019/1                       | 2023/4                    | Régionale                     | Non                                   | Non                                             | Non                                                                 | Oui                                                                     | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3611 | Mesure transitoire - Travailleurs licenciés dans le cadre d'une restructuration - réduction des cotisations patronales - au moins 45 ans                                                                                                                                                                                                             | 2019/1                       | 2023/4                    | Régionale                     | Non                                   | Non                                             | Non                                                                 | Oui                                                                     | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      9001 | Mesure transitoire - Economie d'insertion sociale  moins de 45 ans  624j/36m ou 312j/18m                                                                                                                                                                                                                                                             | 2019/1                       | 2023/4                    | Régionale                     | Non                                   | Non                                             | Non                                                                 | Oui                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# |      3411 | Mesure transitoire - Jeunes travailleurs CPE et très peu qualifiés Ou CPE et moins qualifiés handicapés Ou CPE et moins qualifiés d'origine étrangère                                                                                                                                                                                                | 2019/1                       | 2022/3                    | Régionale                     | Non                                   | Non                                             | Non                                                                 | Oui                                                                     | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3202 | Mesure transitoire - Plan Activa - Demandeurs d'emploi de longue durée  moins de 45 ans  pendant 936 jours dans une période de 54 mois  Codes ONEM : C5  C6  C27  C32 ou C38                                                                                                                                                                         | 2019/1                       | 2021/4                    | Régionale                     | Non                                   | Non                                             | Non                                                                 | Oui                                                                     | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3430 | Mesure transitoire - Jeunes travailleurs : jusqu'au 31/12 de l'année dans laquelle les jeunes auront 18 ans                                                                                                                                                                                                                                          | 2019/1                       | 2021/4                    | Régionale                     | Non                                   | Non                                             | Non                                                                 | Oui                                                                     | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3205 | Mesure transitoire - Plan Activa - Demandeurs d'emploi de longue durée moins de 27 ans  pendant 312 jours dans une période de 18 mois et moins qualifiés Codes ONEM : C40 ou C41  ou à partir du 2014/1 demandeurs d'emploi de longue durée moins de 30 ans  pendant 156 jours dans une période de 9 mois et moins qualifiés Codes ONEM : C42 ou C43 | 2019/1                       | 2021/3                    | Régionale                     | Non                                   | Non                                             | Non                                                                 | Oui                                                                     | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3410 | Mesure transitoire - Jeunes travailleurs CPE et moins qualifiés                                                                                                                                                                                                                                                                                      | 2019/1                       | 2021/3                    | Régionale                     | Non                                   | Non                                             | Non                                                                 | Oui                                                                     | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      3412 | Mesure transitoire - Jeunes travailleurs CPE et moyennement qualifiés                                                                                                                                                                                                                                                                                | 2019/1                       | 2021/3                    | Régionale                     | Non                                   | Non                                             | Non                                                                 | Oui                                                                     | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      6301 | Jeunes travailleurs moyennement qualifiés                                                                                                                                                                                                                                                                                                            | 2016/3                       | 2021/3                    | Régionale                     | Oui                                   | Non                                             | Non                                                                 | Non                                                                     | Interdit       | Obligatoire | Obligatoire        | Occupation de la ligne travailleur | Non                                            |
# |      9000 | Mesure transitoire - Economie d'insertion sociale  moins de 45 ans  312j/18m ou 156j/9m                                                                                                                                                                                                                                                              | 2019/1                       | 2021/2                    | Régionale                     | Non                                   | Non                                             | Non                                                                 | Oui                                                                     | Interdit       | Obligatoire | Interdit           | Occupation de la ligne travailleur | Non                                            |
# +-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------+-------------------------------+---------------------------------------+-------------------------------------------------+---------------------------------------------------------------------+-------------------------------------------------------------------------+----------------+-------------+--------------------+------------------------------------+------------------------------------------------+

# ANNEXE 21: Liste des valeurs autorisées pour le statut du travailleur
# Currently nothing of interest. YTI: The special status could be added on the contract form to manage this in the future.
# under the WorkerStatus tag
# +------+------+--------------------------------------------------------------------------------------------------+------------------------------+---------------------------+,
# | Code | ONSS |                                           Description                                            | Valide à partir du trimestre | Valide jusqu'au trimestre |,
# +------+------+--------------------------------------------------------------------------------------------------+------------------------------+---------------------------+,
# | A    | Yes  | Artiste                                                                                          | 1900/1                       | 2003/2                    |,
# | A1   | Yes  | Artiste avec un contrat de travail                                                               | 2014/1                       | 9999/4                    |,
# | A2   | Yes  | Artiste sans contrat de travail (article 1bis)                                                   | 2014/1                       | 9999/4                    |,
# | B    | No   | Pompiers volontaires                                                                             | 1900/1                       | 2021/4                    |,
# | B    | Yes  | Pompiers volontaires                                                                             | 2022/1                       | 9999/4                    |,
# | BA   | Yes  | Travailleur occupé en dehors du circuit normal du travail                                        | 2020/3                       | 9999/4                    |,
# | C    | No   | Concierges                                                                                       | 1900/1                       | 2021/4                    |,
# | CM   | Yes  | Candidat militaire                                                                               | 1900/1                       | 2003/4                    |,
# | D    | Yes  | Travailleur à domicile                                                                           | 1900/1                       | 9999/4                    |,
# | D1   | Yes  | Travailleur à domicile Accueillants d'enfants Communauté flamande                                | 2015/1                       | 9999/4                    |,
# | D2   | Yes  | Travailleur à domicile Accueillants d'enfants Communauté française                               | 2018/1                       | 9999/4                    |,
# | E    | Yes  | Personnel des établissements d'enseignement qui est déclaré en Dimona auprès (...)               | 2022/1                       | 9999/4                    |,
# | EC   | Yes  | Ministres des cultes et conseillers laïcs                                                        | 2022/1                       | 9999/4                    |,
# | ET   | No   | Statutaire temporaire dans l'enseignement déclaré en Dimona par (...)                            | 2017/2                       | 2021/4                    |,
# | F1   | No   | Stagiaires avec le régime d'indemnisation accident des apprentis                                 | 2020/1                       | 9999/4                    |,
# | F2   | No   | Stagiaires avec un régime d'indemnisation accident autre que celui des apprentis                 | 2020/1                       | 9999/4                    |,
# | LP   | Yes  | Travailleurs avec des prestations réduites                                                       | 2003/1                       | 9999/4                    |,
# | M    | No   | Médecins                                                                                         | 1900/1                       | 2021/4                    |,
# | MA   | Yes  | Mandataires contractuels dans un service public à qui est accordé un complément pension          | 2011/1                       | 9999/4                    |,
# | O    | No   | Personnel des établissements d'enseignement                                                      | 2007/1                       | 2021/4                    |,
# | P    | No   | Personnel de police                                                                              | 1900/1                       | 2021/4                    |,
# | PC   | No   | Personnel civil de police                                                                        | 1900/1                       | 2021/4                    |,
# | RM   | Yes  | Militaire de réserve                                                                             | 2020/1                       | 9999/4                    |,
# | S    | Yes  | Saisonnier                                                                                       | 1900/1                       | 9999/4                    |,
# | SA   | No   | Personnel technique et administratif professionnel des services d'incendie                       | 2013/1                       | 2021/4                    |,
# | SA   | Yes  | Personnel technique et administratif professionnel des services d'incendie                       | 2022/1                       | 9999/4                    |,
# | SP   | No   | Personnel opérationnel professionnel des services d'incendie                                     | 1900/1                       | 2021/4                    |,
# | SP   | Yes  | Personnel opérationnel professionnel des services d'incendie                                     | 2022/1                       | 9999/4                    |,
# | SS   | Yes  | Statutaires stagiaires non assujettis à un régime de pension du secteur public                   | 2017/2                       | 9999/4                    |,
# | T    | Yes  | Temporaire                                                                                       | 1900/1                       | 9999/4                    |,
# | TS   | Yes  | Statutaire temporaire dans l'enseignement rémunéré par (...)                                     | 2017/2                       | 9999/4                    |,
# | TW   | No   | Chercheur d'emploi expérience professionnelle temporaire dans la Région flamande                 | 2019/2                       | 2021/4                    |,
# | TW   | Yes  | Chercheur d'emploi expérience professionnelle temporaire dans la Région flamande                 | 2022/1                       | 9999/4                    |,
# | V    | No   | Personnel soignant  infirmier et paramédical qui n'appartient pas aux secteurs de santé fédéraux | 1900/1                       | 2021/4                    |,
# | V    | Yes  | Personnel soignant  infirmier et paramédical qui n'appartient pas aux secteurs de santé fédéraux | 2022/1                       | 9999/4                    |,
# | VA   | Yes  | Ambulancier volontaire ou volontaire de la Sécurité Civile                                       | 2018/1                       | 9999/4                    |,
# | VF   | No   | Personnel soignant  infirmier et paramédical qui appartient aux secteurs de santé fédéraux       | 2005/1                       | 2021/4                    |,
# | VF   | Yes  | Personnel soignant  infirmier et paramédical qui appartient aux secteurs de santé fédéraux       | 2022/1                       | 9999/4                    |,
# | WF   | Yes  | Personnel des secteurs de santé fédéraux et qui n'est pas du personnel soignant                  | 2022/1                       | 9999/4                    |,
# +------+------+--------------------------------------------------------------------------------------------------+------------------------------+---------------------------+,

class DMFANode:

    def __init__(self, env, sequence=1):
        self.env = env
        self.sequence = sequence

    @classmethod
    def init_multi(cls, args_list):
        """
        Create multiple instances, each with a consecutive sequence number
        :param args_list: list of __init__ parameters
        :return: list of instances
        """
        sequence = 1
        instances = []
        for args in args_list:
            instances.append(cls(*args, sequence=sequence))
            sequence += 1
        return instances


class DMFANaturalPerson(DMFANode):
    """
    Represents an employee or a student
    """
    def __init__(self, employee, payslips, quarter_start, quarter_end, worker_count, sequence=1):
        super().__init__(employee.env, sequence=sequence)
        self.employee = employee
        self.payslips = payslips
        self.identification_id = employee.niss
        self.quarter_start = quarter_start
        self.quarter_end = quarter_end
        self.worker_count = worker_count
        self.worker_records = DMFAWorker.init_multi([(payslips, quarter_start, quarter_end, worker_count)])


class DMFAWorker(DMFANode):
    """
    Represents the employee contracts
    """
    def __init__(self, payslips, quarter_start, quarter_end, worker_count, sequence=1):
        super().__init__(payslips.env, sequence=sequence)
        self.payslips = payslips
        self.quarter_start = quarter_start
        self.quarter_end = quarter_end
        self.worker_count = worker_count

        self.frontier_worker = 0
        self.activity_with_risk = -1

        student_struct = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_student_regular_pay')
        self.student_payslips = payslips.filtered(lambda p: p.struct_id == student_struct)
        payslips = payslips - self.student_payslips

        if self.student_payslips:
            self.worker_code = STUDENT_CODE
        else:
            self.worker_code = WORKER_CODE

        self.local_unit_id = -1 # Deprecated since 2014

        if self.student_payslips:
            self.occupations = []
            skip_remun = False
        else:
            self.occupations = self._prepare_occupations(self.payslips.mapped('contract_id'), self.quarter_start, self.quarter_end)
            skip_remun = all(o.skip_remun for o in self.occupations)

        self.student_contributions = []
        self.contributions = []
        self.deductions = []
        if not skip_remun:
            self.deductions = self._prepare_deductions()
            if self.student_payslips:
                self.student_contributions = self._prepare_student_contributions()
            if payslips:
                self.contributions = self._prepare_contributions()

    def _prepare_student_contributions(self):
        payslips = self.student_payslips
        basis = round(payslips._get_line_values(['BASIC'], compute_sum=True)['BASIC']['sum']['total'], 2)
        contributions = [
            DMFAStudentContribution(self.student_payslips, basis)
        ]
        return contributions

    def _prepare_contributions(self):
        basis_lines = {
            'CP200MONTHLY': 'SALARY',
            'CP200TERM': 'BASIC',
            'CP200THIRTEEN': 'SALARY',
            'CP200HOLN': 'PAY_SIMPLE',
            'CP200HOLN1': 'PAY_SIMPLE',
        }
        # https://www.socialsecurity.be/portail/glossaires/dmfa.nsf/2d585b02976cddabc125686a00590d12/e8361adfc1f6e88cc1256df6002b9948/$FILE/AN2004-1-Fr2.pdf
        contribution_payslips = self.env['hr.payslip']
        for occupation in self.occupations:
            if not occupation.skip_remun:
                contribution_payslips |= occupation.payslips

        # Exclude payslips without remuneration to avoid having a sum of 27€ (ATNs)
        # On a full sick quarter that actually has no presence
        regular_payslips = contribution_payslips.filtered(lambda p: p.struct_id.code == 'CP200MONTHLY')
        regular_payslips_no_remun = regular_payslips.filtered(lambda p: not p.basic_wage)
        no_remun = regular_payslips == regular_payslips_no_remun
        if no_remun:
            contribution_payslips -= regular_payslips

        contribution_payslips = contribution_payslips.filtered(lambda p: p.struct_id.code in basis_lines)
        line_values = contribution_payslips._get_line_values(['SALARY', 'BASIC', 'PAY_SIMPLE'])
        basis = round(sum(line_values[basis_lines[p.struct_id.code]][p.id]['total'] for p in contribution_payslips), 2)

        if not basis:
            return []

        contributions = [
            DMFAWorkerContributionAmiante(contribution_payslips, basis, self.quarter_start)
        ] + [
            DMFAWorkerContributionSpecialWorkAccident(contribution_payslips, basis, self.quarter_start)
        ] + [
            DMFAWorkerContribution(contribution_payslips, basis, self.quarter_start)
        ] + [
            DMFAWorkerContributionFFE(contribution_payslips, basis, self.worker_count, self.quarter_start)
        ] + [
            DMFAWorkerContributionSpecialFFE(contribution_payslips, basis, self.quarter_start)
        ] + [
            DMFAWorkerContributionCPAE(contribution_payslips, basis, self.quarter_start)
        ] + ([
            DMFAWorkerContributionWageRestraint(contribution_payslips, basis, self.quarter_start)
        ] if self.worker_count >= 10 else []) + [
            DMFAWorkerContributionSpecialSocialCotisation(contribution_payslips, basis, self.quarter_start)
        ] + [
            DMFAWorkerContributionTemporaryUnemployment(contribution_payslips, basis, self.quarter_start)
        ]

        return contributions

    def _prepare_occupations(self, contracts, quarter_start, quarter_end):
        def _split_termination_period(date_from, date_to):
            # Split the period into quarters for the current date, and into
            # years for the following dates
            # _split_termination_period(date(2003, 8, 20), date(2005, 2, 10))
            # Returns:
            # [(datetime.date(2003, 8, 20), datetime.date(2003, 9, 30)),
            #  (datetime.date(2003, 10, 1), datetime.date(2003, 12, 31)),
            #  (datetime.date(2004, 1, 1), datetime.date(2004, 12, 31)),
            #  (datetime.date(2005, 1, 1), datetime.date(2005, 2, 10))]
            # _split_termination_period(date(2021, 3, 25), date(2021, 4, 1))
            # [(datetime.date(2021, 3, 25), datetime.date(2021, 3, 31)),
            #  (datetime.date(2021, 4, 1), datetime.date(2021, 4, 1))]
            periods = []
            if date_from == date_to:
                return [(date_from, date_to)]
            boundaries_list = [
                [(1, 1), (31, 3)],
                [(1, 4), (30, 6)],
                [(1, 7), (30, 9)],
                [(1, 10), (31, 12)],
            ]
            current_year = date_from.year
            while date_from < date_to:
                year = date_from.year
                if current_year == year:
                    # Split into quarters
                    for index, boundaries in enumerate(boundaries_list):
                        boundaries_start = boundaries[0]
                        start = date(year, boundaries_start[1], boundaries_start[0])
                        boundaries_end = boundaries[1]
                        end = date(year, boundaries_end[1], boundaries_end[0])
                        if start <= date_from <= end:
                            periods.append((date_from, min(date_to, end)))
                            if date_to < end:
                                return periods
                            if index == 3:
                                date_from = date(year + 1, 1, 1)
                            else:
                                date_from = end + relativedelta(day=1, months=1)
                            if date_from > date_to:
                                return periods
                else:
                    # Split into years
                    end = date_from + relativedelta(day=31, month=12)
                    periods.append((date_from, min(end, date_to)))
                    date_from = end + relativedelta(day=1, month=1, years=1)
            return periods

        values = []
        # Group contracts with the same occupation
        # as they should be declared together
        # Put termination fees in it's own occupation
        occupation_data = contracts._get_occupation_dates()
        termination_occupations = []
        for data in occupation_data:
            occupation_contracts, date_from, date_to = data
            payslips = self.payslips.filtered(lambda p: p.contract_id in occupation_contracts)
            termination_payslips = payslips.filtered(lambda p: p.struct_id.code == 'CP200TERM')
            if termination_payslips:
                # Le salaire et les données relatives aux prestations se rapportant à une indemnité
                # payée suite à une rupture irrégulière de contrat de travail doivent toujours être
                # repris sur une ligne d'occupation distincte (donc séparée des données se
                # rapportant à la période pendant laquelle le contrat de travail a été exécuté).
                # Les règles de distinction qui étaient d'application sous l'ancienne déclaration
                # pour déclarer des indemnités de rupture sont conservées (la partie se rapportant
                # au trimestre pendant lequel le contrat est rompu, la partie se rapportant aux
                # trimestres ultérieurs de l'année civile en cours, la partie se rapportant à
                # chacune des années civiles suivantes). Les dates de début et de fin de cette
                # ligne d'occupation sont celles des périodes couvertes par l'indemnité de rupture.
                # EXEMPLE:
                # Un employé a été licencié le 31 août 2003 et a droit à une indemnité de rupture
                # de 18 mois. Dans ce cas, vous reprenez les données relatives à la rémunération
                # et aux prestations de ce travailleur sur la déclaration du troisième trimestre de
                # 2003 sur cinq lignes d'occupation différentes.
                # - Ligne 1: les données relatives à la période pendant laquelle il y a eu des
                #            prestations c'est-à-dire du 1er juillet 2003 au 31 août 2003 (tenant
                #            compte naturellement du fait que cette période ne doit pas être scindée
                #            en plusieurs lignes d'occupation).
                # - Ligne 2: les données relatives à l'indemnité de rupture pour la période du 1er
                #            septembre 2003 au 30 septembre 2003.
                # - Ligne 3: les données relatives à l'indemnité de rupture pour la période du 1er
                #            octobre 2003 au 31 décembre 2003.
                # - Ligne 4: les données relatives à l'indemnité de rupture pour la période du 1er
                #            janvier 2004 au 31 décembre 2004.
                # - Ligne 5: les données relatives à l'indemnité de rupture pour la période du 1er
                #            janvier 2005 au 28 février 2005 (fin de la période couverte par
                #            l'indemnité de rupture).
                # A l'exception des cas relativement exceptionnels prévus dans la législation sur
                # les contrats de travail prévoyant que de telles indemnités peuvent être payées
                # mensuellement (entreprises en difficulté), les indemnités doivent toujours être
                # reprises intégralement sur la déclaration du trimestre au cours duquel le contrat
                # de travail a été rompu.
                employee = termination_payslips.employee_id
                if not employee.start_notice_period or not employee.end_notice_period:
                    raise UserError(_('No start/end notice period defined for %s', termination_payslips.employee_id.name))
                if employee.start_notice_period > employee.end_notice_period:
                    raise UserError(_('Start notice period is defined after end notice period for %s', termination_payslips.employee_id.name))
                # YTI Check Termination fees
                # Les indemnités considérées comme de la rémunération sont déclarées
                # en DmfA, avec le code rémunération 3 et en mentionnant, pour la période correspondante
                # couverte par la rémunération, le code prestation 1;
                # <Service>
                #   <ServiceSequenceNbr>1</ServiceSequenceNbr>
                #   <ServiceCode>001</ServiceCode>
                #   <ServiceNbrDays>03900</ServiceNbrDays>
                #   <ServiceNbrHours>29640</ServiceNbrHours>
                # </Service>
                # <Remun>
                #   <RemunSequenceNbr>1</RemunSequenceNbr>
                #   <RemunCode>003</RemunCode>
                #   <RemunAmount>00000400546</RemunAmount>
                # </Remun>
                termination_periods = _split_termination_period(
                    employee.start_notice_period, employee.end_notice_period)
                termination_values = termination_payslips._get_line_values(['BASIC'])
                termination_remuneration = sum(termination_values['BASIC'][p.id]['total'] for p in termination_payslips)

                period_remuneration = termination_remuneration / len(termination_periods)
                # values.append((occupation_contracts, termination_payslips, termination_from, termination_to))
                termination_values = [(
                    occupation_contracts,
                    termination_payslips,
                    termination_period[0],
                    termination_period[1],
                ) for termination_period in termination_periods]
                termination_sequence = 90
                termination_occupations = DMFAOccupation.init_multi(termination_values)
                for termination_occupation in termination_occupations:
                    termination_occupation.skip_remun = False
                    termination_occupation.sequence = termination_sequence
                    termination_sequence += 1
                    termination_occupation.services = [DMFANode(termination_payslips.env)]
                    service = termination_occupation.services[0]
                    service.contract = occupation_contracts.sorted(key='date_start', reverse=True)[0]
                    service.code = '001'
                    service.sequence = 99
                    calendar = service.contract.resource_calendar_id
                    dt_from = datetime.combine(termination_occupation.date_start, datetime.min.time())
                    dt_to = datetime.combine(termination_occupation.date_stop, datetime.max.time())
                    occupation_work_data = calendar.get_work_duration_data(
                        dt_from, dt_to, compute_leaves=False)
                    total_days = occupation_work_data['days']
                    total_days = round(total_days * 2) / 2  # Round to half days
                    service.nbr_days = format_amount(total_days, width=5)
                    total_hours = occupation_work_data['hours']
                    service.nbr_hours = format_amount(total_hours, width=5)
                    service.flight_nbr_minutes = -1
                    termination_occupation.remunerations = [DMFANode(termination_payslips.env)]
                    remun = termination_occupation.remunerations[0]
                    remun.code = '003'
                    remun.sequence = 99
                    remun.frequency = -1
                    remun.amount = format_amount(period_remuneration)
                    remun.percentage_paid = -1
            if not termination_payslips and date_to and date_to > quarter_end:
                date_to = False
            values.append((occupation_contracts, payslips - termination_payslips, date_from, date_to))
        return DMFAOccupation.init_multi(values) + termination_occupations

    def _prepare_deductions(self):
        """ Only employement bonus deduction is currently supported """
        employement_bonus_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_employment_bonus_employees')
        employement_deduction_lines = self.payslips.mapped('line_ids').filtered(lambda l: l.salary_rule_id == employement_bonus_rule)
        if employement_deduction_lines:
            return [DMFAWorkerDeduction(employement_deduction_lines, code='0001')]
        return []


class DMFAStudentContribution(DMFANode):
    """
    Represents the paid amounts on the student payslips
    """
    def __init__(self, payslips, basis, sequence=None):
        super().__init__(payslips.env, sequence=sequence)
        work_address = payslips.mapped('contract_id.employee_id.address_id')[0]
        location_unit = self.env['l10n_be.dmfa.location.unit'].search([
            ('partner_id', '=', work_address.id)])
        self.local_unit_id = format_amount(location_unit._get_code(), width=10, hundredth=False)
        self.student_remun_amount = format_amount(basis, width=9)
        self.student_contribution_amount = format_amount(round(basis * 0.0813, 2), width=9)
        self.student_nbr_days = -1
        self.student_hours_nbr = round(payslips._get_worked_days_line_number_of_hours('WORK100'))

class DMFAWorkerContributionSpecialWorkAccident(DMFANode):
    """
    Represents the paid amounts on the employee payslips
    """

    def __init__(self, payslips, basis, quarter_start, sequence=None):
        super().__init__(payslips.env, sequence=sequence)
        self.worker_code = 255
        self.quarter_start = quarter_start
        self.contribution_type = 0
        self.calculation_basis = format_amount(basis)
        rate = payslips.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
            'l10n_be_special_work_accident_rate', date=self.quarter_start, raise_if_not_found=False)
        self.amount = format_amount(round(basis * rate / 100, 2))
        self.first_hiring_date = -1

class DMFAWorkerContributionAmiante(DMFANode):
    """
    Represents the paid amounts on the employee payslips
    """

    def __init__(self, payslips, basis, quarter_start, sequence=None):
        super().__init__(payslips.env, sequence=sequence)
        self.worker_code = 256
        self.quarter_start = quarter_start
        self.contribution_type = 0
        self.calculation_basis = format_amount(basis)
        rate = payslips.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
            'l10n_be_amiante_rate', date=self.quarter_start, raise_if_not_found=False)
        self.amount = format_amount(round(basis * rate / 100, 2))
        self.first_hiring_date = -1

class DMFAWorkerContribution(DMFANode):
    """
    Represents the paid amounts on the employee payslips
    """

    def __init__(self, payslips, basis, quarter_start, sequence=None):
        super().__init__(payslips.env, sequence=sequence)
        self.worker_code = WORKER_CODE
        self.quarter_start = quarter_start
        # Though 2 is the only code for worker 495; see annexe 3
        # the correct value is 0 for 4xx numbers.
        self.contribution_type = 0
        self.calculation_basis = format_amount(basis)
        rate = payslips.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
            'l10n_be_global_rate', date=self.quarter_start, raise_if_not_found=False)
        self.amount = format_amount(round(basis * rate / 100, 2))
        self.first_hiring_date = -1

class DMFAWorkerContributionFFE(DMFANode):
    """
    Represents the paid amounts on the employee payslips - FFE Fond fermeture Entreprise
    """
    def __init__(self, payslips, basis, worker_count, quarter_start, sequence=None):
        super().__init__(payslips.env, sequence=sequence)
        self.worker_code = 809
        self.quarter_start = quarter_start
        self.contribution_type = 5
        self.calculation_basis = format_amount(basis)
        self.worker_count = worker_count
        # Cotisations de base FFE
        rate = payslips[0]._get_ffe_contribution_rate(worker_count)
        self.amount = format_amount(round(basis * rate, 2))
        self.first_hiring_date = -1


class DMFAWorkerContributionSpecialFFE(DMFANode):
    """
    Represents the paid amounts on the employee payslips - Special FFE Fond fermeture Entreprise
    """
    def __init__(self, payslips, basis, quarter_start, sequence=None):
        super().__init__(payslips.env, sequence=sequence)
        self.worker_code = 810
        self.quarter_start = quarter_start
        self.contribution_type = 0
        self.calculation_basis = format_amount(basis)
        # Cotisations de base FFE
        # Tous les employeurs
        # Pour tous les travailleurs soumis à la réglementation sur le chômage
        # 0,13% (0,14%)
        # Source: https://www.socialsecurity.be/employer/instructions/dmfa/fr/latest/instructions/special_contributions/other_specialcontributions/basiccontributions_closingcompanyfunds.html
        rate = payslips.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
            'l10n_be_special_ffe_rate', date=self.quarter_start, raise_if_not_found=False)
        self.amount = format_amount(round(basis * rate / 100, 2))
        self.first_hiring_date = -1


class DMFAWorkerContributionCPAE(DMFANode):
    """
    Represents the paid amounts on the employee payslips - CPAE
    """
    def __init__(self, payslips, basis, quarter_start, sequence=None):
        super().__init__(payslips.env, sequence=sequence)
        self.worker_code = 831
        self.quarter_start = quarter_start
        self.contribution_type = 0
        self.calculation_basis = format_amount(basis)
        # Le Fonds social est financé par la contribution trimestrielle que versent à son profit
        # les entreprises relevant de la CPAE, dont la perception est assurée par l'Office national
        # de sécurité sociale.
        # Les cotisations sont fixées comme suit:
        # Chaque trimestre : 0,23 % de la masse salariale brute
        # Source: https://www.sfonds200.be/fonds-social/qui-sommes-nous
        rate = payslips.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
            'l10n_be_cpae_rate', date=self.quarter_start, raise_if_not_found=False)
        self.amount = format_amount(round(basis * rate / 100, 2))
        self.first_hiring_date = -1


class DMFAWorkerContributionWageRestraint(DMFANode):
    """
    Represents the paid amounts on the employee payslips - Wage Restreint (modération salariale)
    """
    def __init__(self, payslips, basis, quarter_start, sequence=None):
        super().__init__(payslips.env, sequence=sequence)
        self.worker_code = 855
        self.quarter_start = quarter_start
        self.contribution_type = 0
        self.calculation_basis = format_amount(basis)
        # La cotisation de 1,60 % (portée à 1,69 % par l'effet de la cotisation de modération
        # salariale) n'est pas due par tous les employeurs. Elle n'est due que par les employeurs
        # qui, pendant la période de référence, occupaient en moyenne au moins 10 travailleurs.
        # Source: https://www.socialsecurity.be/employer/instructions/dmfa/fr/latest/instructions/socialsecuritycontributions/contributions.html
        rate = payslips.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
            'l10n_be_wage_restreint', date=self.quarter_start, raise_if_not_found=False)
        self.amount = format_amount(round(basis * rate / 100, 2))
        self.first_hiring_date = -1

class DMFAWorkerContributionSpecialSocialCotisation(DMFANode):
    """
    Represents the paid amounts on the employee payslips - Special Social Cotisation
    """
    def __init__(self, payslips, basis, quarter_start, sequence=None):
        super().__init__(payslips.env, sequence=sequence)
        self.worker_code = 856
        self.quarter_start = quarter_start
        self.contribution_type = 0
        self.calculation_basis = -1
        self.amount = format_amount(round(-payslips._get_line_values(['M.ONSS'], compute_sum=True)['M.ONSS']['sum']['total'], 2))
        self.first_hiring_date = -1

class DMFAWorkerContributionTemporaryUnemployment(DMFANode):
    """
    Represents the paid amounts on the employee payslips - Temporary Unemployment
    """
    def __init__(self, payslips, basis, quarter_start, sequence=None):
        super().__init__(payslips.env, sequence=sequence)
        # Source: https://www.socialsecurity.be/employer/instructions/dmfa/fr/latest/instructions/special_contributions/other_specialcontributions/temporary_oldunemployed.html
        self.worker_code = 859
        self.quarter_start = quarter_start
        self.contribution_type = 0
        self.calculation_basis = format_amount(basis)
        rate = payslips.env['hr.rule.parameter'].sudo()._get_parameter_from_code(
            'l10n_be_temporary_unemployment_rate', date=self.quarter_start, raise_if_not_found=False)
        self.amount = format_amount(round(basis * rate / 100, 2))
        self.first_hiring_date = -1


class DMFAOccupation(DMFANode):
    """
    Represents the contract
    """
    def __init__(self, contracts, payslips, date_from, date_to, sequence=1):
        super().__init__(contracts.env, sequence=sequence)

        contract = contracts.sorted(key='date_start', reverse=True)[0]
        calendar = contract.resource_calendar_id
        self.contract = contract
        self.payslips = payslips

        self.date_start = date_from
        self.date_stop = date_to
        if contract.date_end and contract.contract_type_id == self.env.ref('l10n_be_hr_payroll.l10n_be_contract_type_cdd'):
            self.date_stop = contract.date_end

        # See: https://www.socialsecurity.be/employer/instructions/dmfa/fr/latest/instructions/fill_in_dmfa/dmfa_fillinrules/workerrecord_occupationrecords/occupationrecord.html
        if contract.time_credit or contract.resource_calendar_id.work_time_rate < 100:
            if contract.time_credit and contract.time_credit_type_id.code == 'LEAVE300':
                hours_per_week = contract.standard_calendar_id.hours_per_week
            elif contract.time_credit and contract.time_credit_type_id.code == 'LEAVE301':
                hours_per_week = contract.standard_calendar_id.hours_per_week
            else:
                hours_per_week = contract.company_id.resource_calendar_id.hours_per_week
        else:
            hours_per_week = contract.company_id.resource_calendar_id.hours_per_week
        self.ref_mean_working_hours = ('%.2f' % hours_per_week).replace('.', '').zfill(4)

        # Voir Annexe 44: Réorganisation du temps de travail
        if contract.time_credit and contract.time_credit_type_id.code == 'LEAVE300':
            if not contract.resource_calendar_id.hours_per_week:
                self.reorganisation_measure = 3
            else:
                self.reorganisation_measure = 4
        elif contract.time_credit and contract.time_credit_type_id.code == "LEAVE281":
            self.reorganisation_measure = 5
        else:
            self.reorganisation_measure = -1

        self.employment_promotion = -1
        self.worker_status = -1
        self.retired = '0'
        self.apprenticeship = -1
        self.remun_method = -1
        self.position_code = -1
        self.flying_staff_class = -1
        self.TenthOrTwelfth = -1
        self.ActivityCode = -1  # Facultative
        self.days_justification = -1 # YTI: Will be useful for payroll based on attendances

        if contract.time_credit and contract.time_credit_type_id.code == 'LEAVE301':
            # YTI: Could be cleaned by setting calendar correctly at the beginning
            days_per_week = 5.0
            mean_working_hours = 38.0
        else:
            days_per_week = 5 * contract.resource_calendar_id.work_time_rate / 100
            mean_working_hours = contract.resource_calendar_id.hours_per_week

        self.days_per_week = format_amount(days_per_week, width=3)
        self.mean_working_hours = ('%.2f' % mean_working_hours).replace('.', '').zfill(4)

        self.is_parttime = 1 if (not calendar.is_fulltime and not contract.time_credit) else 0

        self.commission = 200  # only CP200 currently supported
        self.services, self.skip_remun = self._prepare_services()
        if not self.skip_remun:
            self.remunerations = self._prepare_remunerations()
        else:
            self.remunerations = []
        self.occupation_informations = self._prepare_occupation_informations()
        work_address = contract.employee_id.address_id
        location_unit = self.env['l10n_be.dmfa.location.unit'].search([('partner_id', '=', work_address.id)])
        self.work_place = format_amount(location_unit._get_code(), width=10, hundredth=False)

    def _prepare_services(self):
        services_by_dmfa_code = defaultdict(lambda: self.env['hr.payslip.worked_days'])
        for wd in self.payslips.mapped('worked_days_line_ids'):
            # Don't declare out of contract + credit time
            if wd.work_entry_type_id.dmfa_code != '-1' and wd.work_entry_type_id.code not in ['OUT', 'LEAVE300', 'LEAVE510']:
                services_by_dmfa_code[wd.work_entry_type_id.dmfa_code] |= wd
        skip_remun = all(dmfa_code in ['30', '50', '52'] for dmfa_code in services_by_dmfa_code.keys())
        return (DMFAService.init_multi([(wds,) for wds in services_by_dmfa_code.values()]), skip_remun)

    def _prepare_remunerations(self):
        # ANNEXE 7: Codification des rémunérations
        # +------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
        # | Code |                                                                                                                                          Libellé                                                                                                                                          |
        # +------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
        # |    1 | Tous les montants qui sont toujours considérés comme rémunération  à l'exception des indemnités mentionnées sous un autre code.                                                                                                                                                           |
        # |    2 | Les primes et les avantages similaires accordés indépendamment du nombre de journées de travail prestées effectivement durant le trimestre de la déclaration.                                                                                                                             |
        # |    3 | Les indemnités qui sont payées au travailleur lorsqu'il est mis fin au contrat de travail et qui sont exprimées en temps de travail.                                                                                                                                                      |
        # |    4 | Indemnités qui sont payées au travailleur lorsqu'il est mis fin au contrat de travail et qui ne sont pas exprimées en temps de travail.                                                                                                                                                   |
        # |    5 | Primes reçues par le travailleur qui limite ses prestations de travail dans le cadre des mesures de redistribution du travail.                                                                                                                                                            |
        # |    6 | Indemnités pour les heures qui ne constituent pas un temps de travail au sens de la loi du 16 mars 1971 sur le travail  accordées en vertu d'une convention collective de travail conclue au sein d'un organe paritaire avant le 1er janvier 1994 et rendue obligatoire par arrêté royal. |
        # |    7 | Pécule simple de vacances de sortie payé aux employés et soumis aux cotisations.                                                                                                                                                                                                          |
        # |    9 | Les indemnités qui sont payées au fonctionnaire statutaire lorsqu'il est mis fin à la relation de travail et qui sont exprimées en temps de travail.                                                                                                                                      |
        # |   10 | Avantage de toute nature sur l'utilisation personnelle d'un véhicule de société ou  jusqu'au 31/12/2020  sur l'allocation de mobilité contre restitution d'un véhicule de société ou sur le véhicule de société respectueux de l'environnement dans le cadre du budget de mobilité.       |
        # |   11 | Pécule simple de vacances de sortie payé aux employés et non soumis aux cotisations.                                                                                                                                                                                                      |
        # |   12 | Partie du pécule simple de vacances qui correspond au salaire normal des jours de vacances et qui a été payé anticipativement par l'employeur précédent et non soumis aux cotisations.                                                                                                    |
        # |   13 | Indemnités pour les heures supplémentaires à ne pas récupérer et non soumises aux cotisations de sécurité sociale                                                                                                                                                                         |
        # |   20 | Eléments constitutifs spécifiques de la rémunération qui sont considérés comme rémunération dans le cas des pensionnés pour l'application des règles en matière de cumul d'une pension de retraite et de survie et un revenu résultant d'une activité professionnelle.                    |
        # |   22 | Rémunération Flexi                                                                                                                                                                                                                                                                        |
        # |   23 | Primes payées à un travailleur flexijob                                                                                                                                                                                                                                                   |
        # |   24 | Avantages non soumis aux cotisations ONSS ordinaires pris en compte pour les subsides                                                                                                                                                                                                     |
        # |   25 | Intervention pour les déplacements en mission                                                                                                                                                                                                                                             |
        # |   26 | Primes et/ou subsides autres que Maribel social perçus par l'employeur                                                                                                                                                                                                                    |
        # |   27 | Indemnité pour un membre d'un parlement ou d'un gouvernement fédéral ou régional ou d'un mandataire local protégé                                                                                                                                                                         |
        # |   28 | Indemnité de sortie d'un membre d'un parlement  d'un gouvernement  d'une Députation permanente ou d'un collège provincial                                                                                                                                                                 |
        # |   29 | Solde du budget mobilité versé en espèces et qui correspond au 3ème pilier                                                                                                                                                                                                                |
        # |   41 | Indemnité pour responsabilités supplémentaires d'un membre du parlement/gouvernement fédéral ou régional                                                                                                                                                                                  |
        # |   51 | Indemnité payée à un membre du personnel nommé à titre définitif qui est totalement absent dans le cadre d'une mesure de réorganisation du temps de travail                                                                                                                               |
        # +------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
        regular_gross = self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_gross_salary')
        student_struct = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_student_regular_pay')
        regular_gross_student = self.env['hr.salary.rule'].search([
            ('struct_id', '=', student_struct.id),
            ('code', '=', 'BASIC'),
        ])
        regular_car = self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_company_car')
        rule_13th_month_gross = self.env.ref('l10n_be_hr_payroll.cp200_employees_thirteen_month_gross_salary')
        termination_n = self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_n_pay_simple')
        termination_n1 = self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_n1_pay_simple')
        termination_fees = self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_fees_basic')
        holiday_pay_recovery_n = self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_holiday_pay_recovery_n', raise_if_not_found=False)
        holiday_pay_recovery_n1 = self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_holiday_pay_recovery_n1', raise_if_not_found=False)
        codes = {
            regular_gross: 1,
            regular_gross_student: 1,
            rule_13th_month_gross: 2,
            termination_n: 7,
            termination_n1: 7,
            regular_car: 10,
            termination_fees: 3,
        }
        if holiday_pay_recovery_n:
            codes[holiday_pay_recovery_n] = 12
            codes[holiday_pay_recovery_n1] = 12
        frequencies = {
            rule_13th_month_gross: 12
        }
        lines_by_code = defaultdict(lambda: self.env['hr.payslip.line'])
        # Exclude payslips without remuneration to avoid having a sum of 27€ (ATNs)
        # On a full sick quarter that actually has no presence
        lines = self.payslips.mapped('line_ids')
        regular_gross_lines = lines.filtered(lambda l: l.salary_rule_id == regular_gross)
        regular_gross_lines_no_remun = regular_gross_lines.filtered(lambda l: not l.slip_id.basic_wage)
        no_remun = regular_gross_lines == regular_gross_lines_no_remun
        for line in self.payslips.mapped('line_ids'):
            if line.salary_rule_id == regular_gross and no_remun:
                continue
            code = codes.get(line.salary_rule_id)
            if code:
                frequency = frequencies.get(line.salary_rule_id)
                lines_by_code[code, frequency] |= line
        # La valeur zéro pour la remuneration est autorisée uniquement pour le solde du budget
        # mobilité (code rémunération 029).
        return DMFARemuneration.init_multi([(
            lines, code, frequency
        ) for (code, frequency), lines in lines_by_code.items() if sum(lines.mapped('total'))])

    def _prepare_occupation_informations(self):
        return DMFAOccupationInformation.init_multi([])


class DMFARemuneration(DMFANode):
    """
    Represents the paid amounts on payslips
    """
    def __init__(self, payslip_lines, code, frequency=None, sequence=1):
        super().__init__(payslip_lines.env, sequence=sequence)
        self.code = str(code).zfill(3)

        if frequency:
            self.frequency = str(frequency).zfill(2)
        else:
            self.frequency = -1

        amount = sum(l.total if l.code not in ['HolPayRecN', 'HolPayRecN1'] else -l.total for l in payslip_lines)
        self.amount = format_amount(amount)

        self.percentage_paid = -1

class DMFAOccupationInformation(DMFANode):
    """
    Represents the paid amounts on payslips
    """
    def __init__(self, sequence=1):
        super().__init__(self.payslips.env, sequence=sequence)

        self.display_info = False

        self.holiday_days_number = -1
        self.six_months_illness_date = -1
        self.maribel = -1
        self.horeca_extra = -1
        self.hour_remun = -1
        self.service_exemption_notion = -1
        self.hour_remun_thousandth = -1
        self.posted_employee = -1
        self.first_week_guaranteed_salary = -1
        self.illness_gross_remun = -1
        self.psddcl_exemption = -1
        self.suppl_pension_exemption = -1
        self.obligation_control = -1
        self.definitive_nomination_date = -1
        self.maribel_date = -1
        self.psp_contrib_derogation = -1
        self.career_measure = -1
        self.sector_detail = -1
        self.mobility_budget = -1
        self.flemish_training_hours = -1
        if self.display_info:
            self.flemish_training_hours = 400
            self.display_info = True
        self.regional_aid_measure = -1


class DMFAService(DMFANode):
    """
    Represents the worked hours/days
    """
    def __init__(self, worked_days, sequence=1):
        super().__init__(worked_days.env, sequence=sequence)
        if len(list(set(worked_days.mapped('work_entry_type_id.dmfa_code')))) > 1:
            raise ValueError("Cannot mix work of different types.")

        self.contract = worked_days.mapped('contract_id').sorted(key='date_start', reverse=True)[0]

        work_entry_type = worked_days[0].work_entry_type_id
        self.code = work_entry_type.dmfa_code.zfill(3)

        total_hours = sum(worked_days.mapped('number_of_hours'))
        total_days = total_hours / 7.6
        total_days = round(total_days * 2) / 2  # Round to half days
        self.nbr_days = format_amount(total_days, width=5)

        self.nbr_hours = format_amount(sum(worked_days.mapped('number_of_hours')), width=5)

        self.flight_nbr_minutes = -1


class DMFAWorkerDeduction(DMFANode):

    def __init__(self, payslip_lines, code, sequence=1):
        super().__init__(payslip_lines.env, sequence=sequence)
        self.code = code
        self.deduction_calculation_basis = -1
        self.amount = format_amount(sum(payslip_lines.mapped('total')))
        # Could be required for other deductions: See ANNEXE 4
        self.deduction_right_starting_date = -1
        self.manager_cost_nbr_months = -1
        self.replace_inss = -1
        self.applicant_inss = -1
        self.certificate_origin = -1


class HrDMFAReport(models.Model):
    _name = 'l10n_be.dmfa'
    _description = 'DMFA xml report'
    _order = "year desc, quarter desc"

    name = fields.Char(compute='_compute_name', store=True)
    reference = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    year = fields.Char(required=True, default=lambda self: fields.Date.today().year)
    quarter = fields.Selection([
        ('1', '1st'),
        ('2', '2nd'),
        ('3', '3rd'),
        ('4', '4th'),
    ], required=True, default=lambda self: str(date_utils.get_quarter_number(fields.Date.today())))
    declaration_type = fields.Selection([
        ('web', 'Via Web',),
        ('batch', 'Via Batch'),
    ], default='web', required=True)
    file_type = fields.Selection([
        ('R', 'Real File (R)'),
        ('S', 'Declaration Test (S)'),
        ('T', 'Circuit Test (T)'),
    ], default='R', required=True)
    dmfa_xml = fields.Binary(string="XML file")
    dmfa_xml_filename = fields.Char(compute='_compute_xml_filename', store=True)
    dmfa_signature = fields.Binary(string="Signature file")
    dmfa_signature_filename = fields.Char(compute='_compute_xml_filename', store=True)
    dmfa_go = fields.Binary(string="Go file")
    dmfa_go_filename = fields.Char(compute='_compute_xml_filename', store=True)
    dmfa_pdf = fields.Binary(string="PDF file")
    dmfa_pdf_filename = fields.Char(compute='_compute_pdf_filename', store=True)
    quarter_start = fields.Date(compute='_compute_dates')
    quarter_end = fields.Date(compute='_compute_dates')
    validation_state = fields.Selection([
        ('normal', "N/A"),
        ('done', "Valid"),
        ('invalid', "Invalid"),
    ], default='normal', compute='_compute_validation_state', store=True)
    error_message = fields.Char(store=True, compute='_compute_validation_state', string="Error Message")

    _sql_constraints = [
        ('_unique', 'unique (company_id, year, quarter)', "Only one DMFA per year and per quarter is allowed. Another one already exists."),
    ]

    @api.depends('reference', 'quarter', 'year')
    def _compute_name(self):
        for dmfa in self:
            dmfa.name = _('%s %s quarter %s', dmfa.reference, dmfa.quarter, dmfa.year)

    @api.constrains('year')
    def _check_year(self):
        for dmfa in self:
            try:
                int(dmfa.year)
            except ValueError:
                raise ValidationError(_("Field Year does not seem to be a year. It must be an integer."))

    @api.depends('dmfa_xml')
    def _compute_validation_state(self):
        dmfa_schema_file_path = file_path('l10n_be_hr_payroll/data/DmfAOriginal_20231.xsd')
        xsd_root = etree.parse(dmfa_schema_file_path)
        schema = etree.XMLSchema(xsd_root)
        for dmfa in self:
            if not dmfa.dmfa_xml:
                dmfa.validation_state = 'normal'
                dmfa.error_message = False
            else:
                xml_root = etree.fromstring(base64.b64decode(dmfa.dmfa_xml))
                try:
                    schema.assertValid(xml_root)
                    dmfa.validation_state = 'done'
                except etree.DocumentInvalid as err:
                    dmfa.validation_state = 'invalid'
                    dmfa.error_message = str(err)

    @api.depends('dmfa_xml')
    def _compute_xml_filename(self):
        # https://www.socialsecurity.be/site_fr/general/helpcentre/batch/files/directives.htm
        num_expedition = self.env["ir.config_parameter"].sudo().get_param("l10n_be.dmfa_expeditor_nbr", False)
        now = fields.Date.today()
        if not num_expedition:
            raise UserError(_('There is no defined expeditor number for the company.'))

        for dmfa in self:
            # Declaration File
            if not dmfa._origin.dmfa_xml_filename:
                num_suite = 0
            else:
                num_suite = dmfa.dmfa_xml_filename.split('.')[4]
                num_suite = str(int(num_suite) + 1)
            num_suite = str(num_suite).zfill(5)
            file_type = dmfa.file_type

            filename_common = '.DMFA.%s.%s.%s.%s.1' % (num_expedition, now.strftime('%Y%m%d'), num_suite, file_type)

            filename = 'FI' + filename_common + '.1'
            dmfa.dmfa_xml_filename = filename

            filename = 'FS'  + filename_common + '.1'
            dmfa.dmfa_signature_filename = filename

            filename = 'GO' + filename_common
            dmfa.dmfa_go_filename = filename

    @api.depends('dmfa_pdf')
    def _compute_pdf_filename(self):
        num_expedition = self.env["ir.config_parameter"].sudo().get_param("l10n_be.dmfa_expeditor_nbr", False)
        now = fields.Date.today()
        if not num_expedition:
            raise UserError(_('There is no defined expeditor number for the company.'))

        for dmfa in self:
            if not dmfa._origin.dmfa_pdf_filename:
                num_suite = 0
            else:
                num_suite = dmfa.dmfa_pdf_filename.split('.')[4]
                num_suite = str(int(num_suite) + 1)
            num_suite = str(num_suite).zfill(5)
            file_type = dmfa.file_type

            filename = 'FI.DMFA.%s.%s.%s.%s.1.1.pdf' % (num_expedition, now.strftime('%Y%m%d'), num_suite, file_type)
            dmfa.dmfa_pdf_filename = filename

    @api.depends('year', 'quarter')
    def _compute_dates(self):
        for dmfa in self:
            year = int(dmfa.year)
            month = int(dmfa.quarter) * 3
            self.quarter_start, self.quarter_end = date_utils.get_quarter(date(year, month, 1))

    def generate_dmfa_xml_report(self):
        # Sources:
        # Procedure: https://www.socialsecurity.be/site_fr/employer/applics/dmfa/batch/outline.htm
        # XML Specification: https://www.socialsecurity.be/site_fr/employer/applics/dmfa/batch/outline.htm
        # Flow Scheme DMFA: https://www.socialsecurity.be/site_fr/general/helpcentre/batch/files/fluxdmfa.htm
        # Structured Annexes: https://www.socialsecurity.be/lambda/portail/glossaires/bijlagen.nsf/web/Bijlagen_Home_Fr
        # General documentation: https://www.socialsecurity.be/site_fr/employer/general/techlib.htm#glossary
        # XML History: https://www.socialsecurity.be/lambda/portail/glossaires/dmfa.nsf/consult/fr/Xmlexport
        # PDF History: https://www.socialsecurity.be/lambda/portail/glossaires/dmfa.nsf/consult/fr/ImprPDF
        # Most related documentation: https://www.socialsecurity.be/lambda/portail/glossaires/dmfa.nsf/web/glossary_home_fr

        # Declaration File
        # ================
        xml_str = self.env['ir.qweb']._render('l10n_be_hr_payroll.dmfa_xml_report', self._get_rendering_data())

        # Prettify xml string
        root = etree.fromstring(xml_str, parser=etree.XMLParser(remove_blank_text=True))
        xml_formatted_str = etree.tostring(root, pretty_print=True, encoding='UTF-8', xml_declaration=True)

        self.dmfa_xml = base64.encodebytes(xml_formatted_str)

        if self.env.context.get('dmfa_skip_signature'):
            return

        # Signature File
        # ==============
        company_sudo = self.company_id.sudo()

        # Load certificate
        pem = company_sudo.onss_pem_certificate
        passphrase = company_sudo.onss_pem_passphrase
        if passphrase:
            passphrase = passphrase.encode()
        else:
            passphrase = None
        if not pem:
            raise UserError(_('No PEM Certificate defined on the Payroll Configuration'))
        pem = base64.b64decode(pem, validate=True)

        # Load key
        ca_key = company_sudo.onss_key
        if not ca_key:
            raise UserError(_('No KEY file defined on the Payroll Configuration'))

        # The PKCS7 signature builder can create both basic PKCS7 signed messages as well as
        # S/MIME messages, which are commonly used in email. S/MIME has multiple versions,
        # but this implements a subset of RFC 2632, also known as S/MIME Version 3.
        # See: https://cryptography.io/en/3.4.8/hazmat/primitives/asymmetric/serialization.html#cryptography.hazmat.primitives.serialization.pkcs7.PKCS7SignatureBuilder
        cert = x509.load_pem_x509_certificate(pem, backend=default_backend())
        key = serialization.load_pem_private_key(pem, password=passphrase, backend=default_backend())
        options = [serialization.pkcs7.PKCS7Options.DetachedSignature]
        sign = serialization.pkcs7.PKCS7SignatureBuilder().set_data(
            self.dmfa_xml
        ).add_signer(
            cert, key, hashes.SHA256()
        ).sign(
            serialization.Encoding.PEM, options
        )
        # Remove -----BEGIN PKCS7-----, -----END PKCS7----- and final new line
        sign = (b'\n').join(sign.split(b'\n')[1:-2])
        self.dmfa_signature = sign

        # GO File
        # =======
        self.dmfa_go = base64.b64encode(b'go')

    def generate_dmfa_pdf_report(self):
        dmfa_pdf, dummy = self.env["ir.actions.report"].sudo()._render_qweb_pdf(
            'l10n_be_hr_payroll.action_report_dmfa',
            res_ids=self.ids, data=self._get_rendering_data())
        self.dmfa_pdf = base64.encodebytes(dmfa_pdf)

    def _get_rendering_data(self):
        payslips = self.env['hr.payslip'].search([
            # ('employee_id', 'in', employees.ids),
            ('date_to', '>=', self.quarter_start),
            ('date_to', '<=', self.quarter_end),
            ('state', 'in', ['done', 'paid']),
            ('company_id', '=', self.company_id.id),
            ('struct_id', '!=', self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_structure_warrant').id),
        ])
        # Exclude CIP contracts from DmfA, as they only have a DIMONA
        contract_type_cip = self.env.ref('l10n_be_hr_payroll.l10n_be_contract_type_cip')
        valid_structure_types = self.env.ref('hr_contract.structure_type_employee_cp200_pfi') \
                              + self.env.ref('hr_contract.structure_type_employee_cp200') \
                              + self.env.ref('l10n_be_hr_payroll.structure_type_student')
        payslips = payslips.filtered(lambda p: p.contract_id.contract_type_id != contract_type_cip and p.contract_id.structure_type_id in valid_structure_types)
        employees = payslips.mapped('employee_id')
        worker_count = len(employees)

        #### Preliminary Checks ####
        # Check Valid ONSS denominations
        if not self.company_id.dmfa_employer_class:
            raise ValidationError(_("Please provide an employer class for company %s. The employer class is given by the ONSS and should be encoded in the Payroll setting.", self.company_id.name))
        if not self.company_id.onss_registration_number and not self.company_id.onss_company_id:
            raise ValidationError(_("No ONSS registration number nor company ID was found for company %s. Please provide at least one.", self.company_id.name))
        # Check valid NISS
        invalid_employees = employees.filtered(lambda e: not e._is_niss_valid())
        if invalid_employees:
            raise UserError(_('Invalid NISS number for those employees:\n %s', '\n'.join(invalid_employees.mapped('name'))))
        # Check valid work addresses
        work_addresses = employees.mapped('address_id')
        location_units = self.env['l10n_be.dmfa.location.unit'].search([('partner_id', 'in', work_addresses.ids)])
        invalid_addresses = work_addresses - location_units.mapped('partner_id')
        invalid_employees = employees.filtered(lambda e: e.address_id in invalid_addresses)
        if invalid_addresses:
            raise UserError(_('The following employees are linked to work addresses without any ONSS identification code:\n %s', '\n'.join(invalid_employees.mapped('name'))))
        # Check valid work entry types
        work_entry_types = payslips.mapped('worked_days_line_ids.work_entry_type_id')
        invalid_types = work_entry_types.filtered(lambda t: not t.dmfa_code)
        if invalid_types:
            raise UserError(_('The following work entry types do not have any DMFA code set:\n %s', '\n'.join(invalid_types.mapped('name'))))

        employee_payslips = defaultdict(lambda: self.env['hr.payslip'])
        for payslip in payslips:
            employee_payslips[payslip.employee_id] |= payslip

        double_basis, double_onss = self._get_double_holiday_pay_contribution(payslips)  # rounded
        group_basis, group_onss = self._get_group_insurance_contribution()

        result = {
            'employer_class': self.company_id.dmfa_employer_class,
            'onss_company_id': format_amount(self.company_id.onss_company_id or 0, width=10, hundredth=False),
            'onss_registration_number': format_amount(self.company_id.onss_registration_number or 0, width=9, hundredth=False),
            'quarter_repr': '%s%s' % (self.year, self.quarter),
            'quarter_display': '%s/%s' % (self.year, self.quarter),
            'quarter_start': self.quarter_start,
            'quarter_end': self.quarter_end,
            'data': self,
            'system5': 0,
            'holiday_starting_date': -1,
            'natural_persons': DMFANaturalPerson.init_multi([(
                employee,
                employee_payslips[employee],
                self.quarter_start,
                self.quarter_end,
                worker_count) for employee in employees]),
            'double_holiday_pay_contribution': format_amount(double_onss),
            'unrelated_calculation_basis': format_amount(double_basis),
            'group_insurance_basis': format_amount(group_basis),
            'group_insurance_amount': format_amount(group_onss),
            'pretty_format': lambda a: str(round(int(a) / 100.0, 2)),
        }

        # Special employer contribution reduction due to 2023 index
        contribution_reduction = 0
        if self.quarter_start.year == 2023 and self.quarter_start.month < 5:
            # The 7.07% contribution reduction is calculated on the overall net basic
            # employer contributions. These are the employer contributions calculated
            # on all the remuneration codes on which the basic employer contributions
            # are calculated (remuneration codes 1, 2, 3, 4, 5, 6, 7, 9, 51, 61, 62,
            # 65 and 66 ) after deduction of applicable employer contribution reductions
            # with the exception of the maribel social package.
            # Source: https://www.socialsecurity.be/employer/instructions/dmfa/fr/latest/instructions/deductions/otheremployersreductions/competitivity_reduction.html
            total_employer_contribution = 0
            # Sum all employer contributions
            for natural_person in result['natural_persons']:
                for worker_record in natural_person.worker_records:
                    for contribution in worker_record.contributions:
                        total_employer_contribution += int(contribution.amount) / 100.0
                    for contribution in worker_record.student_contributions:
                        total_employer_contribution += int(contribution.student_contribution_amount) / 100.0
            # Sum all employee deductions
            for natural_person in result['natural_persons']:
                for worker_record in natural_person.worker_records:
                    for deduction in worker_record.deductions:
                        total_employer_contribution -= int(deduction.amount) / 100.00
            contribution_reduction = round(total_employer_contribution * 7.07 / 100, 2)
            result['employer_compensation'] = format_amount(contribution_reduction)
        else:
            result['employer_compensation'] = 0

        result['global_contribution'] = format_amount(self._get_global_contribution(result['natural_persons'], format_amount(double_onss - contribution_reduction)))
        return result

    def _get_global_contribution(self, employees_infos, double_onss):
        """ Sum of all the owed contributions to ONSS"""
        total = int(double_onss) / 100.0
        # Sum all employer contributions
        for natural_person in employees_infos:
            for worker_record in natural_person.worker_records:
                for contribution in worker_record.contributions:
                    total += int(contribution.amount) / 100.0
                for contribution in worker_record.student_contributions:
                    total += int(contribution.student_contribution_amount) / 100.0
        # Sum all employee contributions
        for natural_person in employees_infos:
            for worker_record in natural_person.worker_records:
                # This isn't correct, but could be. Or is it not?
                # for occupation in worker_record.occupations:
                #     for remuneration in occupation.remunerations:
                #         if remuneration.code != '010':  # Private car reimbursement not under ONSS
                #             total += int(remuneration.amount) / 100.00 * 0.1307
                for deduction in worker_record.deductions:
                    total -= int(deduction.amount) / 100.00
        # https://www.socialsecurity.be/employer/instructions/dmfa/fr/latest/instructions/special_contributions/extralegal_pensions.html#h24
        # En DMFA, la cotisation sur les avantages extra-légaux se déclare globalement par catégorie
        # d’employeur dans le bloc 90002 « cotisation non liée à une personne physique» sous les codes
        # travailleur 864, 865 ou 866 selon le cas.

        # 864 : pour les versements effectués directement au travailleur pensionné ou à ses ayants
        #       droit
        # 865 : pour les versements destinés au financement d'une pension complémentaire dans le cadre
        #       d'un plan d'entreprise
        # 866 : pour les versements destinés au financement d'une pension complémentaire dans le cadre
        #       d'un plan sectoriel
        # ! à partir du 1/2014, cotisation 866 déclarée uniquement par l'organisateur du régime
        #   sectoriel (catégorie X99)
        # Jusqu'au 3ème trimestre 2011 inclus, le code travailleur 851 était d'application mais il
        # n'est plus autorisé pour les trimestres ultérieurs.

        # La base de calcul qui correspond à la somme des avantages octroyés pour l’entreprise par
        # type de versement doit être mentionnée.

        # Lorsque la DMFA est introduite via le web, la base de calcul de cette cotisation doit être
        # mentionnée dans les cotisations dues pour l’ensemble de l’entreprise et la cotisation est
        # calculée automatiquement.
        return round(total, 2) + self._get_group_insurance_contribution()[1]

    def _get_double_holiday_pay_contribution(self, payslips):
        """ Some contribution are not specified at the worker level but globally for the whole company """
        # Montant de la cotisation exeptionnelle (code 870)
        payslips = payslips.filtered(lambda p: not p.contract_id.no_onss)

        basis_lines = {
            'CP200MONTHLY': 'DOUBLE.DECEMBER.SALARY',
            'CP200DOUBLE': 'SALARY',
            'CP200HOLN': 'PAY DOUBLE',
            'CP200HOLN1': 'PAY DOUBLE',
        }
        payslips = payslips.filtered(lambda p: p.struct_id.code in basis_lines)
        line_values = payslips._get_line_values(list(basis_lines.values()))
        basis_raw = sum(line_values[basis_lines[p.struct_id.code]][p.id]['total'] for p in payslips)
        basis = round(basis_raw, 2)
        onss_amount = round(basis_raw * 0.1307, 2)
        return (basis, onss_amount)

    def _get_group_insurance_contribution(self):
        regular_payslip = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary')
        payslips_sudo = self.env['hr.payslip'].sudo().search([
            ('date_to', '>=', self.quarter_start),
            ('date_to', '<=', self.quarter_end),
            ('state', 'in', ['done', 'paid']),
            ('struct_id', '=', regular_payslip.id),
            ('company_id', '=', self.company_id.id),
        ])
        line_values = payslips_sudo._get_line_values(
            ['GROUPINSURANCE'], vals_list=['amount', 'total'], compute_sum=True
        )
        basis = line_values['GROUPINSURANCE']['sum']['amount']
        onss_amount = line_values['GROUPINSURANCE']['sum']['total']
        return (round(basis, 2), round(onss_amount, 2))


class HrDMFALocationUnit(models.Model):
    _name = 'l10n_be.dmfa.location.unit'
    _description = 'Work Place defined by ONSS'
    _rec_name = 'code'

    code = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', string="Working Address", required=True)

    def _get_code(self):
        self.ensure_one()
        return self.code

    _sql_constraints = [
        ('_unique', 'unique (company_id, partner_id)', "A DMFA location cannot be set more than once for the same company and partner."),
    ]
