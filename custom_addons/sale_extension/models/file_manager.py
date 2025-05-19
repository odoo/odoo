from odoo import models, fields
import os
import logging
import base64

_logger = logging.getLogger(__name__)

class FileManager(models.Model):
    _inherit = "sale.order"
    
    quotation_status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed')
    ], string="quotation status", default='draft' )

    def action_save_quotation(self):
        for order in self:
            order.quotation_status = 'confirmed'
            order.sale_file_manager("quotation")
        return True
    
    def sale_file_manager(self, status):
        for order in self:
            try:
                ctx = dict(self.env.context)
                ctx.update({
                    'no_report_file': False,
                    'lang': order.partner_id.lang or 'es_ES',
                })
                pdf_content = self.env['ir.actions.report'].with_context(ctx)._render_qweb_pdf(
                    'sale.report_saleorder', [order.id]
                )[0]


                if(status == "quotation"):
                    output_dir = '/home/demian/archivos_odoo/presupuestos'
                else:
                    output_dir = '/home/demian/archivos_odoo/ordenes'


                os.makedirs(output_dir, exist_ok=True)
                filename = f'Presupuesto_{order.name}.pdf'
                full_path = os.path.join(output_dir, filename)


                with open(full_path, 'wb') as f:
                    f.write(pdf_content)


                _logger.info(f"Presupuesto guardado: {full_path}")

                # Adjuntar
                self.env['ir.attachment'].create({
                    'name': filename,
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': 'sale.order',
                    'res_id': order.id,
                    'mimetype': 'application/pdf',
                })

            except Exception as e:
                _logger.error(f"Error al guardar el presupuesto {order.name}: {e}")