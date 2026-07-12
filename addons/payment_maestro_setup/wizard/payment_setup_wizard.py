# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PaymentSetupWizard(models.TransientModel):
    """Wizard de configuração automática do Stripe e Mercado Pago.

    Lê as credenciais fornecidas pelo usuário e cria/atualiza os registros
    de payment.provider correspondentes, ativando-os automaticamente.
    """
    _name = 'payment.setup.wizard'
    _description = 'Configuração de Pagamentos — Stripe e Mercado Pago'

    # ── Estado atual (lido ao abrir o wizard) ─────────────────────────────────

    stripe_configured = fields.Boolean(compute='_compute_current_state')
    mercado_pago_configured = fields.Boolean(compute='_compute_current_state')

    @api.depends()
    def _compute_current_state(self):
        for rec in self:
            stripe = self.env['payment.provider'].sudo().search(
                [('code', '=', 'stripe'), ('state', '!=', 'disabled')], limit=1)
            mp = self.env['payment.provider'].sudo().search(
                [('code', '=', 'mercado_pago'), ('state', '!=', 'disabled')], limit=1)
            rec.stripe_configured = bool(stripe)
            rec.mercado_pago_configured = bool(mp)

    # ── Stripe ────────────────────────────────────────────────────────────────

    enable_stripe = fields.Boolean(string='Ativar Stripe', default=True,
        help='Cartão de crédito/débito — melhor taxa para assinaturas recorrentes')
    stripe_publishable_key = fields.Char(
        string='Publishable Key',
        placeholder='pk_live_...',
        help='Encontre em stripe.com → Developers → API keys → Publishable key')
    stripe_secret_key = fields.Char(
        string='Secret Key',
        placeholder='sk_live_...',
        help='Encontre em stripe.com → Developers → API keys → Secret key')
    stripe_mode = fields.Selection([
        ('test', 'Teste (Sandbox)'),
        ('live', 'Produção'),
    ], string='Ambiente Stripe', default='live')

    # ── Mercado Pago ──────────────────────────────────────────────────────────

    enable_mercado_pago = fields.Boolean(string='Ativar Mercado Pago', default=True,
        help='PIX, Boleto e Cartão — ideal para clientes pessoa física no Brasil')
    mercado_pago_access_token = fields.Char(
        string='Access Token',
        placeholder='APP_USR-...',
        help='Encontre em mercadopago.com.br → Suas integrações → Credenciais → Access Token de produção')
    mercado_pago_public_key = fields.Char(
        string='Public Key',
        placeholder='APP_USR-...',
        help='Encontre em mercadopago.com.br → Suas integrações → Credenciais → Public Key')
    mercado_pago_mode = fields.Selection([
        ('test', 'Teste (Sandbox)'),
        ('live', 'Produção'),
    ], string='Ambiente Mercado Pago', default='live')

    # ── Validação ─────────────────────────────────────────────────────────────

    @api.constrains('enable_stripe', 'stripe_publishable_key', 'stripe_secret_key')
    def _check_stripe_keys(self):
        for rec in self:
            if rec.enable_stripe:
                if not rec.stripe_publishable_key or not rec.stripe_secret_key:
                    raise UserError(
                        _('Para ativar o Stripe, informe a Publishable Key e a Secret Key.'))
                if not rec.stripe_publishable_key.startswith('pk_'):
                    raise UserError(
                        _('A Publishable Key do Stripe deve começar com "pk_live_" ou "pk_test_".'))
                if not rec.stripe_secret_key.startswith('sk_') and \
                        not rec.stripe_secret_key.startswith('rk_'):
                    raise UserError(
                        _('A Secret Key do Stripe deve começar com "sk_live_" ou "sk_test_".'))

    @api.constrains('enable_mercado_pago', 'mercado_pago_access_token')
    def _check_mercado_pago_keys(self):
        for rec in self:
            if rec.enable_mercado_pago and not rec.mercado_pago_access_token:
                raise UserError(
                    _('Para ativar o Mercado Pago, informe o Access Token.'))

    # ── Ação principal ────────────────────────────────────────────────────────

    def action_apply(self):
        self.ensure_one()
        results = []

        if self.enable_stripe:
            self._setup_stripe()
            results.append('Stripe')

        if self.enable_mercado_pago:
            self._setup_mercado_pago()
            results.append('Mercado Pago')

        if not results:
            raise UserError(_('Ative pelo menos um provedor de pagamento.'))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('✅ Pagamentos configurados!'),
                'message': _(
                    '%s ativado(s) com sucesso. '
                    'Os métodos de pagamento já estão disponíveis para seus clientes.'
                ) % ' e '.join(results),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'payment.provider',
                    'view_mode': 'list,form',
                    'name': _('Provedores de Pagamento'),
                },
            },
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_or_create_provider(self, code, name):
        """Busca um payment.provider existente ou cria um novo."""
        provider = self.env['payment.provider'].sudo().search(
            [('code', '=', code)], limit=1)
        if not provider:
            provider = self.env['payment.provider'].sudo().create({
                'name': name,
                'code': code,
                'state': 'disabled',
            })
        return provider

    def _setup_stripe(self):
        provider = self._get_or_create_provider('stripe', 'Stripe')
        vals = {
            'stripe_publishable_key': self.stripe_publishable_key.strip(),
            'stripe_secret_key': self.stripe_secret_key.strip(),
            'state': 'test' if self.stripe_mode == 'test' else 'enabled',
            'allow_tokenization': True,  # necessário para assinaturas recorrentes
        }
        provider.sudo().write(vals)
        _logger.info('Stripe configurado (modo: %s)', self.stripe_mode)

    def _setup_mercado_pago(self):
        provider = self._get_or_create_provider('mercado_pago', 'Mercado Pago')
        vals = {
            'mercado_pago_access_token': self.mercado_pago_access_token.strip(),
            'state': 'test' if self.mercado_pago_mode == 'test' else 'enabled',
        }
        if self.mercado_pago_public_key:
            vals['mercado_pago_public_key'] = self.mercado_pago_public_key.strip()
            vals['allow_tokenization'] = True
        provider.sudo().write(vals)
        _logger.info('Mercado Pago configurado (modo: %s)', self.mercado_pago_mode)
