from odoo import models, fields, api
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Campo personalizado para el 15% del MVP
    descuento_maximo_permitido = fields.Float(
        string='Descuento Máximo Permisible (%)', 
        default=15.0
    )

    # Añadimos el nuevo estado "Requiere Revisión" al flujo de ventas nativo
    state = fields.Selection(
        selection_add=[('requires_review', 'Requiere Revisión')],
        ondelete={'requires_review': 'set default'}
    )

    # Forzamos la validación tanto al guardar como al hacer clic en Confirmar
    def action_confirm(self):
        for order in self:
            # Revisa si alguna línea de producto supera el límite establecido
            supera_limite = any(line.discount > order.descuento_maximo_permitido for line in order.order_line)
            
            if supera_limite:
                # Cambiamos el estado del documento a tu estado personalizado
                order.write({'state': 'requires_review'})
                
                # Lanzamos el aviso en la pantalla que detiene la confirmación automática
                raise UserError("¡Alerta de Control (MVP)! Este pedido supera el 15% de descuento permitido. El presupuesto ha sido retenido en estado 'Requiere Revisión' para la aprobación de Diego.")
        
        # Si no hay ningún descuento inflado, Odoo sigue su camino normal de confirmación
        return super(SaleOrder, self).action_confirm()
