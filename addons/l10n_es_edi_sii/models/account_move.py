# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import Counter, defaultdict
import math

from odoo import api, fields, models, modules, tools
from odoo.exceptions import LockError, UserError
from odoo.tools.float_utils import float_round
from markupsafe import Markup
from odoo.tools.sql import SQL

L10N_ES_SII_MAX_BATCH_SIZE = 10000


class AccountMove(models.Model):
    _inherit = 'account.move'

    # -------------------------------------------------------------------------
    # SII FIELDS
    # -------------------------------------------------------------------------

    l10n_es_registration_date = fields.Date(
        string="Registration Date",
        copy=False,
        help="Date when the invoice was registered in the SII system.",
    )
    l10n_es_edi_sii_document_ids = fields.One2many(
        comodel_name='l10n_es_edi_sii.document',
        inverse_name='move_id',
        string="SII Documents",
    )
    l10n_es_edi_is_required = fields.Boolean(
        string="Is the Spanish EDI needed",
        compute='_compute_l10n_es_edi_is_required',
    )
    l10n_es_edi_sii_state = fields.Selection(
        selection=[
            ('to_send', "To Send"),
            ('sent', "Sent"),
            ('cancelled', "Cancelled"),
        ],
        string="Spain SII Status",
        compute='_compute_l10n_es_edi_sii_data',
        search='_search_l10n_es_edi_sii_state',
    )
    l10n_es_edi_csv = fields.Char(
        string="CSV",
        compute='_compute_l10n_es_edi_sii_data',
        help="Secure Verification Code of the last accepted document",
    )
    l10n_es_edi_sii_error = fields.Html(
        string="SII Error",
        compute='_compute_l10n_es_edi_sii_data',
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends(
        'l10n_es_edi_is_required',
        'l10n_es_edi_sii_document_ids.state',
        'l10n_es_edi_sii_document_ids.csv',
    )
    def _compute_l10n_es_edi_sii_data(self):
        for move in self:
            docs = move.l10n_es_edi_sii_document_ids
            if not move.l10n_es_edi_is_required or not docs:
                move.l10n_es_edi_sii_state = 'to_send' if move.l10n_es_edi_is_required else False
                move.l10n_es_edi_csv = False
                move.l10n_es_edi_sii_error = False
                continue

            sorted_docs = docs.sorted('create_date', reverse=True)
            latest_doc = sorted_docs[:1]
            accepted_docs = sorted_docs.filtered(lambda d: d.state in ('accepted', 'accepted_with_errors'))
            move.l10n_es_edi_csv = accepted_docs[:1].csv

            if latest_doc.state in ('accepted', 'accepted_with_errors'):
                move.l10n_es_edi_sii_state = 'sent'
                move.l10n_es_edi_sii_error = latest_doc.response_message if latest_doc.state == 'accepted_with_errors' else False
            elif latest_doc.state == 'cancelled':
                move.l10n_es_edi_sii_state = 'cancelled'
                move.l10n_es_edi_sii_error = False
            else:
                move.l10n_es_edi_sii_state = 'sent' if accepted_docs else 'to_send'
                move.l10n_es_edi_sii_error = latest_doc.response_message

    @api.depends('move_type', 'company_id', 'invoice_line_ids.tax_ids')
    def _compute_l10n_es_edi_is_required(self):
        for move in self:
            has_tax = not move.is_purchase_document() or any(t.l10n_es_type and t.l10n_es_type != 'ignore' for t in move.invoice_line_ids.tax_ids)

            move.l10n_es_edi_is_required = (
                move.is_invoice()
                and move.country_code == 'ES'
                and move.company_id.l10n_es_sii_tax_agency
                and has_tax
            )

    @api.depends('l10n_es_edi_is_required', 'l10n_es_edi_sii_state')
    def _compute_need_cancel_request(self):
        super()._compute_need_cancel_request()
        for move in self:
            if move.l10n_es_edi_is_required and move.l10n_es_edi_sii_state == 'sent':
                move.need_cancel_request = True

    @api.depends('l10n_es_edi_is_required', 'l10n_es_edi_sii_state')
    def _compute_show_reset_to_draft_button(self):
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.l10n_es_edi_is_required and move.l10n_es_edi_sii_state == 'sent':
                move.show_reset_to_draft_button = True

    def button_request_cancel(self):
        res = super().button_request_cancel()
        for move in self:
            if move.l10n_es_edi_is_required and move.l10n_es_edi_sii_state == 'sent':
                move._send_l10n_es_sii_document(cancel=True)
        return res

    def _l10n_es_is_dua(self):
        self.ensure_one()
        mapped_taxes = self.invoice_line_ids.tax_ids.flatten_taxes_hierarchy()
        return any(t.l10n_es_type == 'dua' for t in mapped_taxes)

    def _get_l10n_es_sii_state_query_parts(self, state):
        query_str = """
            SELECT am.id
              FROM account_move am
              LEFT JOIN LATERAL (
                  SELECT d.state
                    FROM l10n_es_edi_sii_document d
                   WHERE d.move_id = am.id
                   ORDER BY d.create_date DESC, d.id DESC
                   LIMIT 1
              ) latest ON TRUE
              LEFT JOIN LATERAL (
                  SELECT 1 AS found
                    FROM l10n_es_edi_sii_document d
                   WHERE d.move_id = am.id
                     AND d.state IN ('accepted', 'accepted_with_errors')
                   LIMIT 1
              ) accepted ON TRUE
             WHERE am.move_type IN ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')
               AND am.company_id IN (
                   SELECT comp.id
                   FROM res_company comp
                   JOIN res_partner p ON p.id = comp.partner_id
                   JOIN res_country c ON c.id = COALESCE(comp.account_fiscal_country_id, p.country_id)
                   WHERE c.code = 'ES' AND comp.l10n_es_sii_tax_agency IS NOT NULL
               )
               AND (
                   am.move_type NOT IN ('in_invoice', 'in_refund')
                   OR EXISTS (
                       SELECT 1 FROM account_move_line aml
                       JOIN account_move_line_account_tax_rel rel ON rel.account_move_line_id = aml.id
                       JOIN account_tax t ON t.id = rel.account_tax_id
                       WHERE aml.move_id = am.id AND t.l10n_es_type IS NOT NULL AND t.l10n_es_type != 'ignore'
                   )
               )
               AND CASE
                   WHEN latest.state IS NULL                               THEN 'to_send'
                   WHEN latest.state IN ('accepted', 'accepted_with_errors') THEN 'sent'
                   WHEN latest.state = 'cancelled'                         THEN 'cancelled'
                   WHEN accepted.found IS NOT NULL                         THEN 'sent'
                   ELSE 'to_send'
               END = %s
        """
        return query_str, (state,)

    def _get_l10n_es_sii_state_move_ids(self, state):
        query_str, params = self._get_l10n_es_sii_state_query_parts(state)
        self.env.cr.execute(SQL(query_str, params))
        return [row[0] for row in self.env.cr.fetchall()]

    def _search_l10n_es_edi_sii_state(self, operator, value):
        if isinstance(value, str):
            states = [value]
        else:
            states = list(value)

        if operator in ('=', 'in'):
            move_ids = set()
            for state in states:
                move_ids.update(self._get_l10n_es_sii_state_move_ids(state))
            return [('id', 'in', list(move_ids))]
        elif operator in ('!=', 'not in'):
            excluded_states = set(states)
            move_ids = set()
            for state in ('to_send', 'sent', 'cancelled'):
                if state not in excluded_states:
                    move_ids.update(self._get_l10n_es_sii_state_move_ids(state))
            return [('id', 'in', list(move_ids))]
        else:
            raise NotImplementedError()

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _l10n_es_sii_lock_move(self):
        """ Acquire a write lock on the invoices in self. """
        try:
            self.lock_for_update()
        except LockError:
            if len(self) == 1:
                raise UserError(self.env._('Cannot send this entry as it is already being processed.'))
            raise UserError(self.env._('Cannot send these entries as they are already being processed.'))

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------

    def action_l10n_es_send_sii(self):
        self.ensure_one()
        self._send_l10n_es_sii_document()
        return {
            'type': 'ir.actions.client',
            'tag': 'soft_reload',
        }

    def action_l10n_es_sii_send_in_batch(self):
        """ Groups selected invoices and sends them to SII via batched payloads. """
        moves_to_process = self.filtered(lambda m: m.l10n_es_edi_is_required and m.state == 'posted')
        batches = moves_to_process.grouped(lambda m: (m.company_id, m.is_sale_document(), bool(m.l10n_es_edi_csv)))
        result = True

        for batch_moves in batches.values():
            for i in range(0, len(batch_moves), L10N_ES_SII_MAX_BATCH_SIZE):
                chunk = batch_moves[i:i + L10N_ES_SII_MAX_BATCH_SIZE]
                result = chunk._send_l10n_es_sii_document_batch(allow_raising_lock=False) and result
                if not tools.config['test_enable'] and not modules.module.current_test:
                    self.env.cr.commit()
        return result

    # -------------------------------------------------------------------------
    # BUSINESS LOGIC
    # -------------------------------------------------------------------------

    def _send_l10n_es_sii_document(self, cancel=False):
        """ Creates doc, calls webservice and updates states. """
        self.ensure_one()
        batches = self.grouped(lambda m: (m.company_id, m.is_sale_document(), not cancel and m.l10n_es_edi_csv))

        self._l10n_es_sii_lock_move()
        result = True
        for moves in batches.values():
            result = moves._send_l10n_es_sii_document_batch(cancel=cancel) and result
        return result

    def _send_l10n_es_sii_document_batch(self, cancel=False, allow_raising_lock=True):
        """ Creates docs, calls webservice and updates states. """
        target_state = 'to_cancel' if cancel else 'to_send'
        document_ids = []
        move_ids_to_send = []

        if allow_raising_lock:
            self._l10n_es_sii_lock_move()
        else:
            self = self.try_lock_for_update()
            if not self:
                return False

        for move in self:
            document = move.l10n_es_edi_sii_document_ids.filtered(lambda d: d.state == target_state)[:1]
            if not document:
                document = self.env['l10n_es_edi_sii.document'].sudo().create({
                    'move_id': move.id,
                    'state': target_state,
                })
            errors = move._l10n_es_sii_check_move_configuration()
            if errors:
                document.sudo().write({
                    'response_message': Markup("%s<br/>%s") % (
                        self.env._("Invalid invoice configuration:"),
                        Markup("<br/>").join(errors)
                    )
                })
                continue
            document_ids.append(document.id)
            move_ids_to_send.append(move.id)

        move_ids_to_send_set = set(move_ids_to_send)
        document_ids_set = set(document_ids)
        moves_to_send = self.filtered(lambda move: move.id in move_ids_to_send_set)
        documents = moves_to_send.l10n_es_edi_sii_document_ids.filtered(lambda document: document.id in document_ids_set)

        if not documents:
            return False

        communication_type = moves_to_send[:1].l10n_es_edi_csv and not cancel and 'A1' or 'A0'
        info_list = moves_to_send._l10n_es_edi_get_invoices_info()

        # Trigger the document model to handle the actual sending
        results = documents._post_to_web_service(info_list, communication_type)
        if len(documents) == 1:
            results = {documents: results}

        # Retry logic for 1117
        if any(result.get('error_1117') for result in results.values()) and not self.env.context.get('error_1117'):
            documents.sudo().unlink()
            return moves_to_send.with_context(error_1117=True)._send_l10n_es_sii_document_batch(cancel=cancel, allow_raising_lock=allow_raising_lock)

        return True

    def _l10n_es_sii_check_move_configuration(self):
        self.ensure_one()
        company = self.company_id
        errors = []

        if self.env['res.partner']._is_vat_void(company.vat):
            errors.append(self.env._("VAT number is missing on company %s.", company.display_name))

        if not company.l10n_es_sii_certificate_id:
            errors.append(self.env._("Please configure the certificate for SII."))

        if not company.l10n_es_sii_tax_agency:
            errors.append(self.env._("Please specify a tax agency on your company for SII."))

        if self.move_type in ('in_invoice', 'in_refund') and not self.ref:
            errors.append(self.env._("You should put a vendor reference on this vendor bill."))

        lines = self.invoice_line_ids.filtered(
            lambda l: l.display_type not in ('line_section', 'line_subsection', 'line_note')
        )

        for line in lines:
            taxes = line.tax_ids.flatten_taxes_hierarchy()
            l10n_types_count = Counter(taxes.mapped('l10n_es_type'))
            duplicate_types = {t for t, count in l10n_types_count.items() if count > 1}
            if duplicate_types:
                errors.append(
                    self.env._(
                        "Line %(line_name)s has duplicate tax types: %(tax_types)s",
                        line_name=line.display_name,
                        tax_types=", ".join(duplicate_types),
                    )
                )

            main_tax_count = (
                l10n_types_count.get('sujeto', 0)
                + l10n_types_count.get('no_sujeto', 0)
                + l10n_types_count.get('no_sujeto_loc', 0)
            )
            if main_tax_count > 1:
                errors.append(
                    self.env._("Line %s should only have one main tax type.", line.display_name)
                )

        all_taxes = lines.tax_ids.flatten_taxes_hierarchy()
        is_foreign = self.commercial_partner_id._l10n_es_is_foreign()

        if self.is_outbound() and is_foreign and all_taxes and not any(t.tax_scope for t in all_taxes):
            errors.append(
                self.env._(
                    "In case of a foreign customer, you need to configure the tax scope on taxes. Please configure tax scope on taxes: %s",
                    ", ".join(all_taxes.mapped('name'))
                )
            )

        return errors

    def _l10n_es_edi_get_invoices_info(self):
        return [move._l10n_es_edi_get_invoice_info() for move in self]

    def _l10n_es_edi_get_invoice_info(self):
        self.ensure_one()
        if not self.l10n_es_registration_date:
            self.l10n_es_registration_date = fields.Date.context_today(self)

        info = {
            'PeriodoLiquidacion': {
                'Ejercicio': str(self.date.year),
                'Periodo': str(self.date.month).zfill(2),
            },
            'IDFactura': {
                'FechaExpedicionFacturaEmisor': self.invoice_date.strftime('%d-%m-%Y'),
            },
        }

        com_partner = self.commercial_partner_id
        is_simplified = self.l10n_es_is_simplified

        if self.is_sale_document():
            invoice_node = info['FacturaExpedida'] = {}
        else:
            invoice_node = info['FacturaRecibida'] = {}

        partner_info = com_partner._l10n_es_edi_get_partner_info()

        if self.delivery_date and self.delivery_date != self.invoice_date:
            invoice_node['FechaOperacion'] = self.delivery_date.strftime('%d-%m-%Y')

        if self.invoice_origin:
            invoice_node['DescripcionOperacion'] = self.invoice_origin[:500]
        else:
            invoice_node['DescripcionOperacion'] = 'manual'

        reagyp = self.invoice_line_ids.tax_ids.filtered(lambda t: t.l10n_es_type == 'sujeto_agricultura')

        if self.is_sale_document():
            if self.company_id.vat and self.company_id.vat.startswith('ES'):
                nif = self.company_id.vat[2:]
            else:
                nif = self.company_id.vat

            info['IDFactura']['IDEmisorFactura'] = {'NIF': nif}
            info['IDFactura']['NumSerieFacturaEmisor'] = self.name[:60]

            if not is_simplified:
                invoice_node['Contraparte'] = {
                    **partner_info,
                    'NombreRazon': com_partner.name[:120]
                }

            invoice_node['ClaveRegimenEspecialOTrascendencia'] = self.invoice_line_ids.tax_ids._l10n_es_get_regime_code()

        else:
            if self._l10n_es_is_dua():
                partner_info = self.company_id.partner_id._l10n_es_edi_get_partner_info()

            info['IDFactura']['IDEmisorFactura'] = partner_info
            info["IDFactura"]["IDEmisorFactura"].update({"NombreRazon": com_partner.name[0:120]})
            info["IDFactura"]["NumSerieFacturaEmisor"] = (self.ref or "")[:60]

            if not is_simplified:
                invoice_node['Contraparte'] = {
                    **partner_info,
                    'NombreRazon': com_partner.name[:120]
                }

            invoice_node['FechaRegContable'] = self.l10n_es_registration_date.strftime('%d-%m-%Y')

            mod_303_10 = self.env.ref('l10n_es.mod_303_casilla_10_balance')._get_matching_tags()
            mod_303_11 = self.env.ref('l10n_es.mod_303_casilla_11_balance')._get_matching_tags()
            tax_tags = self.invoice_line_ids.tax_ids.repartition_line_ids.tag_ids
            intracom = bool(tax_tags & (mod_303_10 + mod_303_11))

            if intracom:
                invoice_node['ClaveRegimenEspecialOTrascendencia'] = '09'
            elif reagyp:
                invoice_node['ClaveRegimenEspecialOTrascendencia'] = '02'
            else:
                invoice_node['ClaveRegimenEspecialOTrascendencia'] = '01'

        if self.move_type == 'out_invoice':
            invoice_node['TipoFactura'] = 'F2' if is_simplified else 'F1'
        elif self.move_type == 'out_refund':
            invoice_node['TipoFactura'] = 'R5' if is_simplified else 'R1'
            invoice_node['TipoRectificativa'] = 'I'
        elif self.move_type == 'in_invoice':
            if reagyp:
                invoice_node['TipoFactura'] = 'F6'
            elif self._l10n_es_is_dua():
                invoice_node['TipoFactura'] = 'F5'
            else:
                invoice_node['TipoFactura'] = 'F1'
        elif self.move_type == 'in_refund':
            invoice_node['TipoFactura'] = 'R4'
            invoice_node['TipoRectificativa'] = 'I'

        sign = -1 if self.is_refund() else 1

        if self.is_sale_document():
            if not com_partner._l10n_es_is_foreign() or is_simplified:
                tax_details_info_vals = self._l10n_es_edi_get_invoices_tax_details_info()
                invoice_node['TipoDesglose'] = {'DesgloseFactura': tax_details_info_vals['tax_details_info']}

                total_amount = (
                    tax_details_info_vals['tax_details']['base_amount']
                    + tax_details_info_vals['tax_details']['tax_amount']
                    - tax_details_info_vals['tax_amount_retention']
                )
                invoice_node['ImporteTotal'] = float_round(sign * total_amount, 2)
            else:
                tax_details_info_service_vals = self._l10n_es_edi_get_invoices_tax_details_info(
                    filter_invl_to_apply=lambda x: any(t.tax_scope == 'service' for t in x.tax_ids)
                )

                tax_details_info_consu_vals = self._l10n_es_edi_get_invoices_tax_details_info(
                    filter_invl_to_apply=lambda x: any(t.tax_scope == 'consu' for t in x.tax_ids)
                )

                desglose_operacion = invoice_node.setdefault('TipoDesglose', {}).setdefault('DesgloseTipoOperacion', {})

                if tax_details_info_service_vals['tax_details_info']:
                    desglose_operacion['PrestacionServicios'] = tax_details_info_service_vals['tax_details_info']

                if tax_details_info_consu_vals['tax_details_info']:
                    desglose_operacion['Entrega'] = tax_details_info_consu_vals['tax_details_info']

                service_total = (
                    tax_details_info_service_vals['tax_details']['base_amount']
                    + tax_details_info_service_vals['tax_details']['tax_amount']
                    - tax_details_info_service_vals['tax_amount_retention']
                )
                consu_total = (
                    tax_details_info_consu_vals['tax_details']['base_amount']
                    + tax_details_info_consu_vals['tax_details']['tax_amount']
                    - tax_details_info_consu_vals['tax_amount_retention']
                )
                invoice_node['ImporteTotal'] = float_round(sign * (service_total + consu_total), 2)
        else:
            tax_details_info_isp_vals = self._l10n_es_edi_get_invoices_tax_details_info(
                filter_invl_to_apply=lambda x: any(t.l10n_es_type == 'sujeto_isp' for t in x.tax_ids)
            )

            tax_details_info_other_vals = self._l10n_es_edi_get_invoices_tax_details_info(
                filter_invl_to_apply=lambda x: not any(t.l10n_es_type == 'sujeto_isp' for t in x.tax_ids)
            )

            invoice_node['DesgloseFactura'] = {}
            if tax_details_info_isp_vals['tax_details_info']:
                invoice_node['DesgloseFactura']['InversionSujetoPasivo'] = tax_details_info_isp_vals['tax_details_info']

            if tax_details_info_other_vals['tax_details_info']:
                invoice_node['DesgloseFactura']['DesgloseIVA'] = tax_details_info_other_vals['tax_details_info']

            has_ignore_tax = any(t.l10n_es_type == 'ignore' for t in self.invoice_line_ids.tax_ids)
            if self._l10n_es_is_dua() or has_ignore_tax:
                isp_total = (
                    tax_details_info_isp_vals['tax_details']['base_amount']
                    + tax_details_info_isp_vals['tax_details']['tax_amount']
                )
                other_total = (
                    tax_details_info_other_vals['tax_details']['base_amount']
                    + tax_details_info_other_vals['tax_details']['tax_amount']
                )
                invoice_node['ImporteTotal'] = float_round(sign * (isp_total + other_total), 2)
            else:
                retention_isp = sign * tax_details_info_isp_vals['tax_amount_retention']
                retention_other = sign * tax_details_info_other_vals['tax_amount_retention']

                invoice_node['ImporteTotal'] = float_round(
                    -self.amount_total_signed - retention_isp - retention_other, 2
                )

            total_deductible = (
                tax_details_info_isp_vals['tax_amount_deductible']
                + tax_details_info_other_vals['tax_amount_deductible']
            )
            invoice_node['CuotaDeducible'] = float_round(sign * total_deductible, 2)

        return info

    def _l10n_es_edi_get_invoices_tax_details_info(self, filter_invl_to_apply=None):
        def grouping_key_generator(base_line, tax_data):
            tax = tax_data['tax']
            return {
                'applied_tax_amount': tax.amount,
                'l10n_es_type': tax.l10n_es_type,
                'l10n_es_exempt_reason': tax.l10n_es_exempt_reason if tax.l10n_es_type == 'exento' else False,
                'l10n_es_bien_inversion': tax.l10n_es_bien_inversion,
            }

        def filter_to_apply(base_line, tax_data):
            return (
                not tax_data['is_reverse_charge']
                and tax_data['tax'].amount != -100.0
                and tax_data['tax'].l10n_es_type != 'ignore'
            )

        def full_filter_invl_to_apply(invoice_line):
            mapped_taxes = invoice_line.tax_ids.flatten_taxes_hierarchy().mapped('l10n_es_type')
            if all(t == 'ignore' for t in mapped_taxes):
                return False
            return filter_invl_to_apply(invoice_line) if filter_invl_to_apply else True

        tax_details = self._prepare_invoice_aggregated_taxes(
            filter_invl_to_apply=full_filter_invl_to_apply,
            filter_tax_values_to_apply=filter_to_apply,
            grouping_key_generator=grouping_key_generator,
        )

        sign = -1 if self.is_refund() else 1
        tax_details_info = defaultdict(dict)
        recargo_tax_details = defaultdict(lambda: defaultdict(float))

        for base_line in tax_details['base_lines']:
            line = base_line['record']
            taxes = line.tax_ids.flatten_taxes_hierarchy()
            recargo_tax = taxes.filtered(lambda t: t.l10n_es_type == 'recargo')[:1]

            if recargo_tax and taxes:
                recargo_main_tax = taxes.filtered(lambda x: x.l10n_es_type in ('sujeto', 'sujeto_isp'))[:1]
                aggregated_values = tax_details['tax_details_per_record'][line]

                recargo_values = next(iter(
                    values for values in aggregated_values['tax_details'].values()
                    if values['grouping_key']
                    and values['grouping_key']['l10n_es_type'] == recargo_tax.l10n_es_type
                    and values['grouping_key']['applied_tax_amount'] == recargo_tax.amount
                ))

                dict_key = (recargo_main_tax.l10n_es_type, recargo_main_tax.amount)
                recargo_tax_details[dict_key]['tax_amount'] += recargo_values['tax_amount']
                recargo_tax_details[dict_key]['applied_tax_amount'] = recargo_values['applied_tax_amount']

        tax_amount_deductible = 0.0
        tax_amount_retention = 0.0
        base_amount_not_subject = 0.0
        base_amount_not_subject_loc = 0.0
        tax_subject_info_list = []
        tax_subject_isp_info_list = []

        for tax_values in tax_details['tax_details'].values():
            recargo = recargo_tax_details.get((tax_values['l10n_es_type'], tax_values['applied_tax_amount']))

            if self.is_sale_document():
                match tax_values['l10n_es_type']:
                    case 'sujeto' | 'sujeto_isp':
                        tax_amount_deductible += tax_values['tax_amount']
                        base_amount = sign * tax_values['base_amount']

                        tax_info = {
                            'TipoImpositivo': tax_values['applied_tax_amount'],
                            'BaseImponible': float_round(base_amount, 2),
                            'CuotaRepercutida': float_round(math.copysign(tax_values['tax_amount'], base_amount), 2)
                        }

                        if recargo:
                            tax_info['CuotaRecargoEquivalencia'] = float_round(sign * recargo['tax_amount'], 2)
                            tax_info['TipoRecargoEquivalencia'] = recargo['applied_tax_amount']

                        if tax_values['l10n_es_type'] == 'sujeto':
                            tax_subject_info_list.append(tax_info)
                        else:
                            tax_subject_isp_info_list.append(tax_info)

                    case 'exento':
                        exenta_dict = tax_details_info.setdefault('Sujeta', {}).setdefault('Exenta', {'DetalleExenta': []})
                        exenta_dict['DetalleExenta'].append({
                            'BaseImponible': float_round(sign * tax_values['base_amount'], 2),
                            'CausaExencion': tax_values['l10n_es_exempt_reason']
                        })
                    case 'retencion':
                        tax_amount_retention += tax_values['tax_amount']
                    case 'no_sujeto':
                        base_amount_not_subject += tax_values['base_amount']
                    case 'no_sujeto_loc':
                        base_amount_not_subject_loc += tax_values['base_amount']

            else:
                match tax_values['l10n_es_type']:
                    case 'sujeto' | 'sujeto_isp' | 'dua':
                        tax_amount_deductible += tax_values['tax_amount']
                    case 'no_sujeto':
                        tax_amount_deductible += tax_values['tax_amount']
                        base_amount_not_subject += tax_values['base_amount']
                    case 'no_sujeto_loc':
                        tax_amount_deductible += tax_values['tax_amount']
                        base_amount_not_subject_loc += tax_values['base_amount']
                    case 'retencion':
                        tax_amount_retention += tax_values['tax_amount']
                    case 'ignore':
                        continue

                if tax_values['l10n_es_type'] not in ['retencion', 'recargo', 'ignore']:
                    base_amount = sign * tax_values['base_amount']
                    tax_info = {'BaseImponible': float_round(base_amount, 2)}

                    if tax_values['l10n_es_type'] == 'sujeto_agricultura':
                        tax_info.update({
                            'PorcentCompensacionREAGYP': tax_values['applied_tax_amount'],
                            'ImporteCompensacionREAGYP': float_round(math.copysign(tax_values['tax_amount'], base_amount), 2)
                        })
                    elif tax_values['applied_tax_amount'] > 0.0:
                        tax_info.update({
                            'TipoImpositivo': tax_values['applied_tax_amount'],
                            'CuotaSoportada': float_round(math.copysign(tax_values['tax_amount'], base_amount), 2)
                        })

                    if tax_values['l10n_es_bien_inversion']:
                        tax_info['BienInversion'] = 'S'

                    if recargo:
                        tax_info['CuotaRecargoEquivalencia'] = float_round(sign * recargo['tax_amount'], 2)
                        tax_info['TipoRecargoEquivalencia'] = recargo['applied_tax_amount']

                    tax_details_info.setdefault('DetalleIVA', []).append(tax_info)

        if tax_subject_isp_info_list and not tax_subject_info_list:
            tax_details_info.setdefault('Sujeta', {})['NoExenta'] = {'TipoNoExenta': 'S2'}
        elif not tax_subject_isp_info_list and tax_subject_info_list:
            tax_details_info.setdefault('Sujeta', {})['NoExenta'] = {'TipoNoExenta': 'S1'}
        elif tax_subject_isp_info_list and tax_subject_info_list:
            tax_details_info.setdefault('Sujeta', {})['NoExenta'] = {'TipoNoExenta': 'S3'}

        if tax_subject_info_list:
            no_exenta_dict = tax_details_info['Sujeta']['NoExenta']
            no_exenta_dict.setdefault('DesgloseIVA', {}).setdefault('DetalleIVA', []).extend(tax_subject_info_list)

        if tax_subject_isp_info_list:
            no_exenta_dict = tax_details_info['Sujeta']['NoExenta']
            no_exenta_dict.setdefault('DesgloseIVA', {}).setdefault('DetalleIVA', []).extend(tax_subject_isp_info_list)

        if not self.company_id.currency_id.is_zero(base_amount_not_subject) and self.is_sale_document():
            tax_details_info.setdefault('NoSujeta', {})['ImportePorArticulos7_14_Otros'] = float_round(sign * base_amount_not_subject, 2)

        if not self.company_id.currency_id.is_zero(base_amount_not_subject_loc) and self.is_sale_document():
            tax_details_info.setdefault('NoSujeta', {})['ImporteTAIReglasLocalizacion'] = float_round(sign * base_amount_not_subject_loc, 2)

        if not tax_details_info and self.is_sale_document():
            has_no_sujeto = any(t['l10n_es_type'] == 'no_sujeto' for t in tax_details['tax_details'].values())
            if has_no_sujeto:
                tax_details_info.setdefault('NoSujeta', {})['ImportePorArticulos7_14_Otros'] = 0

            has_no_sujeto_loc = any(t['l10n_es_type'] == 'no_sujeto_loc' for t in tax_details['tax_details'].values())
            if has_no_sujeto_loc:
                tax_details_info.setdefault('NoSujeta', {})['ImporteTAIReglasLocalizacion'] = 0

        return {
            'tax_details_info': tax_details_info,
            'tax_details': tax_details,
            'tax_amount_deductible': tax_amount_deductible,
            'tax_amount_retention': tax_amount_retention,
            'base_amount_not_subject': base_amount_not_subject,
            'S1_list': tax_subject_info_list,
            'S2_list': tax_subject_isp_info_list,
        }
