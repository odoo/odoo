# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_pe_withhold_code = fields.Selection(
        selection=[
            ('001', 'Azúcar y melaza de caña'),
            ('002', 'Arroz'),
            ('003', 'Alcohol etílico'),
            ('004', 'Recursos hidrobiológicos'),
            ('005', 'Maíz amarillo duro'),
            ('006', 'Algodón (Obsoleto)'),
            ('007', 'Caña de azúcar'),
            ('008', 'Madera'),
            ('009', 'Arena y piedra'),
            ('010', 'Residuos, subproductos, desechos, recortes y desperdicios'),
            ('011', 'Bienes gravados con el IGV, o renuncia a la exoneración'),
            ('012', 'Intermediación laboral y tercerización'),
            ('013', 'Animales vivos'),
            ('014', 'Carnes y despojos comestibles'),
            ('015', 'Abonos, cueros y pieles de origen animal'),
            ('016', 'Aceite de pescado'),
            ('017', 'Harina, polvo y “pellets” de pescado, crustáceos, moluscos y demás invertebrados acuáticos'),
            ('018', 'Embarcaciones pesqueras (Obsoleto)'),
            ('019', 'Arrendamiento de bienes muebles'),
            ('020', 'Mantenimiento y reparación de bienes muebles'),
            ('021', 'Movimiento de carga'),
            ('022', 'Otros servicios empresariales'),
            ('023', 'Leche'),
            ('024', 'Comisión mercantil'),
            ('025', 'Fabricación de bienes por encargo'),
            ('026', 'Servicio de transporte de personas'),
            ('027', 'Servicio de transporte de carga'),
            ('028', 'Transporte de pasajeros'),
            ('029', 'Algodón en rama sin desmontar (Obsoleto)'),
            ('030', 'Contratos de construcción'),
            ('031', 'Oro gravado con el IGV'),
            ('032', 'Páprika y otros frutos de los géneros capsicum o pimienta'),
            ('033', 'Espárragos (Obsoleto)'),
            ('034', 'Minerales metálicos no auríferos'),
            ('035', 'Bienes exonerados del IGV'),
            ('036', 'Oro y demás minerales metálicos exonerados del IGV'),
            ('037', 'Demás servicios gravados con el IGV'),
            ('039', 'Minerales no metálicos'),
            ('040', 'Bien inmueble gravado con IGV'),
            ('041', 'Plomo'),
            ('099', 'Ley 30737'),
        ],
        string="Withhold code",
        help="Peru: Catalog No. 54 SUNAT, used functionally to show in the printed document on invoices that need to "
             "have the proper SPOT text.")
    l10n_pe_withhold_percentage = fields.Float(
        string="Withhold Percentage",
        help="Peru: Percentages of detraction informed in the Annex I Resolution 183-2004/SUNAT, it depends on the "
             "withhold code but you need to read the resolution.")
