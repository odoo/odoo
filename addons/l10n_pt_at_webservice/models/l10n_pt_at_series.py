import logging

from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import LockError, UserError
from odoo.tools.zeep.exceptions import Error as ZeepError

from odoo.addons.l10n_pt_at_webservice.const import PT_AT_DOCUMENT_TYPE_MAPPING, PT_AT_MEIO_PROCESSAMENTO
from odoo.addons.l10n_pt_at_webservice.utils.series_ws import ATSeriesError
from odoo.addons.l10n_pt_certification.const import PT_CERTIFICATION_NUMBER

_logger = logging.getLogger(__name__)


class L10nPtATSeries(models.Model):
    _inherit = "l10n_pt.at.series"

    l10n_pt_at_ws_offline = fields.Boolean(compute='_compute_l10n_pt_at_ws_offline')
    l10n_pt_at_ws_registration_date = fields.Date(
        string="Registered with the AT on",
        readonly=True,
        copy=False,
        help="The day the AT registered the series through the webservice; empty when its code was entered by hand.",
    )
    l10n_pt_at_ws_annulment_date = fields.Date(
        string="Annulled at the AT on",
        readonly=True,
        copy=False,
    )
    l10n_pt_at_ws_can_annul = fields.Boolean(compute='_compute_l10n_pt_at_ws_can_annul')
    l10n_pt_at_ws_finalization_date = fields.Date(
        string="Finalised at the AT on",
        readonly=True,
        copy=False,
    )
    l10n_pt_at_ws_can_finalize = fields.Boolean(compute='_compute_l10n_pt_at_ws_can_finalize')
    l10n_pt_at_ws_error = fields.Char(
        string="Registration Error",
        readonly=True,
        copy=False,
        help="Why the series could not be registered with the AT when it was created.",
    )

    @api.depends('company_id')
    def _compute_l10n_pt_at_ws_offline(self):
        for series in self:
            series.l10n_pt_at_ws_offline = series.company_id.root_id.sudo().l10n_pt_at_ws_env == 'offline'

    def _l10n_pt_at_ws_today(self):
        """Today in Lisbon, the AT's day."""
        return fields.Date.context_today(self.with_context(tz='Europe/Lisbon'))

    @api.depends('at_code', 'l10n_pt_at_ws_registration_date', 'l10n_pt_at_ws_annulment_date', 'company_id')
    def _compute_l10n_pt_at_ws_can_annul(self):
        # The AT annuls a series only on the day it registered it or the next day, and only one in
        # which no document was issued.
        earliest = self._l10n_pt_at_ws_today() - timedelta(days=1)
        candidates = self.filtered(lambda s: (
            s._origin
            and s.at_code
            and s.l10n_pt_at_ws_registration_date
            and s.l10n_pt_at_ws_registration_date >= earliest
            and not s.l10n_pt_at_ws_annulment_date
            and not s.l10n_pt_at_ws_offline
        ))
        used = candidates._origin._l10n_pt_get_used()
        for series in self:
            series.l10n_pt_at_ws_can_annul = series in candidates and series._origin not in used

    def _l10n_pt_at_ws_issue_state(self):
        """
        For each series of ``self``: whether a document was issued in it, and whether one is
        numbered but not issued yet (an invoice posted on the series' last day, issued later).
        """
        issued, pending = set(), set()
        for model_name in self._l10n_pt_document_models():
            # sudo: a series shared across branches holds documents of companies the user may not see.
            documents = self.env[model_name].sudo()
            series_domain = [('l10n_pt_at_series_id', 'in', self.ids)]
            for ids, domain in (
                (issued, [*series_domain, ('l10n_pt_issued_on', '!=', False)]),
                (pending, [*series_domain, ('l10n_pt_issued_on', '=', False), *documents._l10n_pt_numbered_domain()]),
            ):
                [(series,)] = documents._read_group(domain, aggregates=['l10n_pt_at_series_id:recordset'])
                ids.update(series.ids)
        return {series: (series.id in issued, series.id in pending) for series in self}

    def _l10n_pt_at_ws_last_issued_number(self):
        """The number, in the series, of its last issued document: the one the AT knows it by."""
        self.ensure_one()
        numbers = [0]
        for model_name in self._l10n_pt_document_models():
            # sudo: a series shared across branches holds documents of companies the user may not see.
            documents = self.env[model_name].sudo().search_fetch(
                [('l10n_pt_at_series_id', '=', self.id), ('l10n_pt_issued_on', '!=', False)],
                ['l10n_pt_document_number'],
            )
            numbers += [document._l10n_pt_get_sequence_number() for document in documents]
        return max(numbers)

    @api.depends('at_code', 'date_end', 'l10n_pt_at_ws_finalization_date', 'l10n_pt_at_ws_annulment_date', 'company_id')
    def _compute_l10n_pt_at_ws_can_finalize(self):
        # Finalising is optional, and no document may be issued in the series afterwards: only an
        # ended series, all of whose numbered documents are issued, and which has issued one.
        today = self._l10n_pt_at_ws_today()
        candidates = self.filtered(lambda s: (
            s._origin
            and s.at_code
            and s.date_end and s.date_end < today
            and not s.l10n_pt_at_ws_finalization_date
            and not s.l10n_pt_at_ws_annulment_date
            and not s.l10n_pt_at_ws_offline
        ))
        states = candidates._origin._l10n_pt_at_ws_issue_state()
        for series in self:
            issued, pending = states.get(series._origin, (False, True))
            series.l10n_pt_at_ws_can_finalize = series in candidates and issued and not pending

    def write(self, vals):
        if 'date_end' in vals and self.filtered('l10n_pt_at_ws_finalization_date'):
            raise UserError(self.env._("The end of a series finalised at the AT cannot be changed."))
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.at_code:
                continue
            company = record.company_id.root_id.sudo()
            if company.l10n_pt_at_ws_env == 'offline' or not company.l10n_pt_at_ws_username:
                continue
            # A series is created whether or not the AT registers it: it can be registered later,
            # or its code entered by hand. The user is told why it was not registered.
            try:
                with self.env.cr.savepoint():
                    record.action_register_at_series()
            except (UserError, ValueError, OSError, ZeepError) as e:
                _logger.warning(
                    "Failed to auto-register AT series %(name)s (type: %(type)s)",
                    {'name': record.name, 'type': record.document_type},
                    exc_info=True,
                )
                record._l10n_pt_at_ws_notify_error(e.args[0] if isinstance(e, UserError) else str(e))
        return records

    def _l10n_pt_at_ws_notify_error(self, message):
        """Keep on the series why it was not registered, and tell the user at once."""
        self.ensure_one()
        self.l10n_pt_at_ws_error = message
        self.env.user._bus_send('simple_notification', {
            'type': 'warning',
            'sticky': True,
            'title': self.env._("AT series %(series)s saved without validation code", series=self.document_identifier),
            'message': self.env._(
                "%(error)s — Register it again from the series, or enter the code obtained from the Portal das Finanças.",
                error=message,
            ),
        })

    def _l10n_pt_at_ws_get_registration_params(self):
        self.ensure_one()
        mapping = PT_AT_DOCUMENT_TYPE_MAPPING.get(self.document_type)
        if not mapping:
            raise UserError(self.env._(
                "Series of type %(type)s cannot be registered with the AT webservice.",
                type=self.document_type_name or self.document_type,
            ))
        # The AT refuses an expected start of use before its own today, and treats the date as
        # indicative only: documents may be issued before it. The series keeps its own start date,
        # which decides the documents it numbers.
        today_lisbon = fields.Date.context_today(self.with_context(tz='Europe/Lisbon'))
        return {
            'serie': self.name,
            'tipoSerie': 'F' if self.training_series else 'N',
            'classeDoc': mapping['classeDoc'],
            'tipoDoc': mapping['tipoDoc'],
            'numInicialSeq': 1,
            'dataInicioPrevUtiliz': max(self.date_start, today_lisbon),
            'numCertSWFatur': int(PT_CERTIFICATION_NUMBER),
            'meioProcessamento': PT_AT_MEIO_PROCESSAMENTO,
        }

    def action_register_at_series(self):
        self.ensure_one()
        # Series are communicated per NIF, which branches share with their root company: the
        # webservice is configured on the root company only.
        company = self.company_id.root_id.sudo()
        if company.l10n_pt_at_ws_env == 'offline':
            raise UserError(self.env._(
                "The AT webservice is offline for company %(company)s: enter the validation code obtained "
                "from the Portal das Finanças, or choose its environment in the Accounting Settings.",
                company=company.name,
            ))

        if self.l10n_pt_at_ws_annulment_date:
            raise UserError(self.env._(
                "The series %(series)s was annulled at the AT: its name can never be registered again for this document type.",
                series=self.document_identifier,
            ))
        company._l10n_pt_at_ws_check_configuration()
        # Registering cannot be undone: concurrent registrations of a series make one call, and a
        # series registered meanwhile is not sent again.
        try:
            self.lock_for_update()
        except LockError:
            raise UserError(self.env._(
                "The series %(series)s is being registered with the AT right now. Please try again in a moment.",
                series=self.document_identifier,
            )) from None
        self.invalidate_recordset(['at_code'])
        if self.at_code:
            return

        if company.l10n_pt_at_ws_env == 'test' and not self.training_series:
            self.training_series = True

        params = self._l10n_pt_at_ws_get_registration_params()
        with company._l10n_pt_at_ws_series_client() as client:
            try:
                info_serie = client.register(**params)
            except ATSeriesError as e:
                if e.code != 4001:
                    raise
                # Already registered: read the series back; when that fails too, the AT's refusal says more.
                try:
                    info_serie = self._l10n_pt_at_ws_find_registered_series(client, params)
                except (ATSeriesError, ZeepError, OSError):
                    info_serie = False
                if not info_serie:
                    raise e from None
        self.write({
            'at_code': info_serie.codValidacaoSerie,
            'l10n_pt_at_ws_registration_date': getattr(info_serie, 'dataRegisto', None) or self._l10n_pt_at_ws_today(),
            'l10n_pt_at_ws_error': False,
        })

    def _l10n_pt_at_ws_find_registered_series(self, client, params):
        """
        The series (``infoSerie``) the AT already registered with these parameters, if any.

        Registering is a call the database transaction cannot undo: when the transaction is rolled
        back after the AT registered the series (a replayed request, a later error), the AT refuses
        every new attempt as already registered (4001). The code is then read back from the AT: its
        active series of that name, document class and type, and kind (training or normal).
        """
        for info_serie in client.query(serie=params['serie'], classeDoc=params['classeDoc'], tipoDoc=params['tipoDoc']):
            if (
                info_serie.estado == 'A'
                and info_serie.tipoSerie == params['tipoSerie']
                and (info_serie.serie or '').upper() == params['serie'].upper()
                and info_serie.codValidacaoSerie
            ):
                at_code = info_serie.codValidacaoSerie
                # sudo: the series holding the code may belong to another company of the same NIF
                holder = self.sudo().with_context(active_test=False).search([('at_code', '=', at_code), ('id', '!=', self.id)], limit=1)
                if holder:
                    raise UserError(self.env._(
                        "The AT has already registered a series %(name)s of this document type, whose code %(code)s is "
                        "that of the series %(series)s of company %(company)s. Series are registered once per tax number: "
                        "use that series, or give this one another name.",
                        name=self.name, code=at_code, series=holder.document_identifier, company=holder.company_id.name,
                    ))
                return info_serie
        return False

    def action_l10n_pt_at_ws_annul(self):
        """
        Annul at the AT a series registered by mistake (anularSerie): on the day the AT registered it
        or the next day, when no document was issued in it. The AT never accepts its name again for
        this document type, so the series is kept, ended and without code.
        """
        self.ensure_one()
        company = self.company_id.root_id.sudo()
        try:
            self.lock_for_update()
        except LockError:
            raise UserError(self.env._(
                "The series %(series)s is being changed right now. Please try again in a moment.",
                series=self.document_identifier,
            )) from None
        self.invalidate_recordset()
        if not self.l10n_pt_at_ws_can_annul:
            raise UserError(self.env._(
                "The series %(series)s cannot be annulled: the AT annuls only a series it registered through "
                "the webservice today or yesterday, in which no document was numbered.",
                series=self.document_identifier,
            ))
        mapping = PT_AT_DOCUMENT_TYPE_MAPPING[self.document_type]
        with company._l10n_pt_at_ws_series_client() as client:
            client.annul(
                serie=self.name,
                classeDoc=mapping['classeDoc'],
                tipoDoc=mapping['tipoDoc'],
                codValidacaoSerie=self.at_code,
                motivo='ER',  # Anulação por erro de registo
                declaracaoNaoEmissao=True,  # no document was issued in the series
            )
        today = self._l10n_pt_at_ws_today()
        self.write({
            'at_code': False,
            'date_end': today - timedelta(days=1),
            'l10n_pt_at_ws_annulment_date': today,
            'l10n_pt_at_ws_error': False,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': self.env._(
                    "The series %(series)s was annulled at the AT. It is kept, ended, so that its name is not used again.",
                    series=self.document_identifier,
                ),
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    def action_l10n_pt_at_ws_finalize(self):
        """
        Finalise at the AT an ended series (finalizarSerie), with the number of its last issued
        document. Optional for the AT; no document may be issued in the series afterwards.
        """
        self.ensure_one()
        company = self.company_id.root_id.sudo()
        try:
            self.lock_for_update()
        except LockError:
            raise UserError(self.env._(
                "The series %(series)s is being changed right now. Please try again in a moment.",
                series=self.document_identifier,
            )) from None
        self.invalidate_recordset()
        if not self.l10n_pt_at_ws_can_finalize:
            raise UserError(self.env._(
                "The series %(series)s cannot be finalised: only a series with an AT code, ended, with issued "
                "documents and none numbered but not issued yet, can be.",
                series=self.document_identifier,
            ))
        last_issued = self._l10n_pt_at_ws_last_issued_number()
        mapping = PT_AT_DOCUMENT_TYPE_MAPPING[self.document_type]
        with company._l10n_pt_at_ws_series_client() as client:
            client.finalize(
                serie=self.name,
                classeDoc=mapping['classeDoc'],
                tipoDoc=mapping['tipoDoc'],
                codValidacaoSerie=self.at_code,
                seqUltimoDocEmitido=last_issued,
            )
        self.l10n_pt_at_ws_finalization_date = self._l10n_pt_at_ws_today()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': self.env._(
                    "The series %(series)s was finalised at the AT, its last document being number %(number)s.",
                    series=self.document_identifier, number=last_issued,
                ),
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }
