from odoo import models, fields, api
class TnSociete(models.Model):
    _name = "tn.societe"
    _description = "Société simple (nom uniquement)"
    _rec_name = "name"

    name = fields.Char(string="Nom de la société", required=True)
    # taux  cotisations sociales
    btn = fields.Boolean(string="affich tableau cnss ")
    vp = fields.Float(string="vp")
    vs = fields.Float(string="vs")
    mp = fields.Float(string="mp")
    ms = fields.Float(string="ms")
    fp = fields.Float(string="fp")
    fs = fields.Float(string="fs")
    pre = fields.Float(string="pre")
    pre1 = fields.Float(string="pre1")

    # taux  retraite complementaire
    btn1 = fields.Boolean(string="affich tableau retrait ")
    rp = fields.Float(string="rp")
    rs = fields.Float(string="rs")

    # irpp
    btn2 = fields.Boolean(string="affich tableau IRPP ")

    taux = fields.Float(string="taux", )
    brutau = fields.Float(string="brutau")
    brutdu = fields.Float(string="brutdu")
    taux1 = fields.Float(string="taux", )
    brutau1 = fields.Float(string="brutau")
    brutdu1 = fields.Float(string="brutdu")
    taux2 = fields.Float(string="taux", )
    brutau2 = fields.Float(string="brutau")
    brutdu2 = fields.Float(string="brutdu")
    taux3 = fields.Float(string="taux", )
    brutau3 = fields.Float(string="brutau")
    brutdu3 = fields.Float(string="brutdu")
    taux4 = fields.Float(string="taux", )
    brutau4 = fields.Float(string="brutau")
    brutdu4 = fields.Float(string="brutdu")