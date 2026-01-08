import hashlib
import json
import logging
from datetime import timedelta
from typing import Any

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Domain
from odoo.models import BaseModel
from odoo.tools.constants import GC_UNLINK_LIMIT
from odoo.tools.misc import consteq, hash_sign, verify_hash_signed
from odoo.tools.sql import SQL, column_exists, create_column


_logger = logging.getLogger(__name__)


class IrAccessToken(models.Model):
    _name = 'ir.access.token'
    _description = 'Access Token'

    res_model = fields.Char('Model', required=True, readonly=True)
    res_id = fields.Many2oneReference('Record', model_field='res_model', required=True, readonly=True)
    scope = fields.Char('Scope', required=True, readonly=True)
    expiration = fields.Datetime('Expiration', readonly=True, index='btree')
    owner_id = fields.Many2one('res.users', readonly=True, ondelete='cascade')
    json_extra = fields.Char('JSON Extra', readonly=True)

    _res_idx = models.Index('(res_model, res_id)')

    def _auto_init(self):
        super()._auto_init()
        if not column_exists(self.env.cr, 'ir_access_token', 'manual_token'):
            create_column(self.env.cr, 'ir_access_token', 'manual_token', 'VARCHAR')

    @api.autovacuum
    def _gc_access_token(self):
        self.search(
            [('expiration', '<', self.env.cr.now())],
            limit=GC_UNLINK_LIMIT,
        ).unlink()

    def write(self, vals):
        raise UserError(self.env._("Cannot update access tokens"))

    def action_open_record(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def __generate(
        self,
        res_model: str,
        res_id: int,
        scope: str,
        duration: timedelta | None = None,
        owner_id: int | None = None,
        extra: Any = None,
        manual_token: str | None = None,
    ) -> str:
        """ Generate an access token.

        :param res_model: target model name.
        :param res_id: record id.
        :param scope: access scope associated with the token.
        :param duration: optional expiration timedelta for the token,
                         if `None`, the token does not expire.
        :param owner_id: optional id identifying the token owner.
        :param extra: optional extra information stored in the token (must be serializable).
        :param manual_token: optional token value which must be forced.
        :return: signed access token string.
        """
        assert not (extra and manual_token), "A manual token cannot contain additional information."
        assert self.env.su, "Sudo environment is required to generate access token."

        expiration = None
        if duration is not None:
            if duration.total_seconds() <= 0:
                raise ValidationError(self.env._("Duration must be positive."))
            expiration = self.env.cr.now() + duration

        json_extra = json.dumps(extra) if extra is not None else None

        access_token = self.create({
            'res_model': res_model,
            'res_id': res_id,
            'scope': scope,
            'expiration': expiration,
            'owner_id': owner_id,
            'json_extra': json_extra,
        })

        if manual_token:
            self.env.cr.execute(SQL("""
                UPDATE %(table)s SET manual_token = %(manual_token)s WHERE id = %(id)s
            """,
                table=SQL.identifier(self._table),
                manual_token=manual_token,
                id=access_token.id,
            ))

        _logger.info(
            "User %d generates access tokens (%s): %s, %s, %s, %s, %s (%s)",
            self.env.uid, access_token.id, res_model, res_id, scope, expiration, owner_id,
            'manual' if manual_token else 'auto',
        )

        # Include the access token ID in the signed payload to ensure we have a
        # different token if we need to regenerate one for the same record.
        return manual_token or hash_sign(
            self.env, scope, (access_token.id, res_model, res_id, owner_id, json_extra and hashlib.sha256(json_extra.encode()).hexdigest()), expiration
        )

    @api.model
    def __retrieve_sudo_record(
        self,
        model: str, scope: str, token: str, *,
        res_model: str | None = None,
        res_id: int | None = None,
    ) -> BaseModel:
        """ Get the referenced sudoed record by the token.

        :param model: target model name.
        :param scope: access scope associated with the token.
        :param token: access token identifying the record.
        :param res_model: model name (required for manual token or retrieve from the payload)
        :param res_id: record id (required for manual token or retrieve from the payload)
        :return: sudoed record.
        :raises AccessError:
            - if the token is invalid, expired, or does not match the expected scope or payload,
            - if the model record doesn't match the target model,
            - if the owner of the token doesn't match the user environment,
            - if the token has been revoked.
        """
        assert self.env.su, "Sudo environment is required to retrieve a record from access token."

        try:
            payload = verify_hash_signed(self.env, scope, token)
        except ValueError:
            assert res_model and res_id, "Manual tokens require record identification."

            query = self._search([
                ('res_model', '=', res_model),
                ('res_id', '=', res_id),
                ('scope', '=', scope),
                '|', ('owner_id', '=', False), ('owner_id', '=', self.env.uid),
                '|', ('expiration', '=', False), ('expiration', '>', self.env.cr.now()),
            ], order='owner_id NULLS FIRST, expiration DESC NULLS FIRST, id')

        else:  # Correct token format
            if payload is None:  # Token is invalid
                raise AccessError(self.env._("Invalid token: incorrect scope or expired."))

            access_token_id, res_model, res_id, owner_id, _ = payload
            if owner_id and owner_id != self.env.uid:
                raise AccessError(self.env._("Invalid token: incorrect owner."))

            query = self._search([('id', '=', access_token_id)])

        if res_model != model:
            raise AccessError(self.env._("Invalid token: incorrect model."))

        query = query.select(
            query.table.id,
            query.table.res_model,
            query.table.res_id,
            query.table.scope,
            query.table.expiration,
            query.table.owner_id,
            query.table.json_extra,
            SQL("%s", SQL.identifier(query.table._alias, 'manual_token')),
        )

        for access_token_id, res_model, res_id, scope, expiration, owner_id, json_extra, manual_token in self.env.execute_query(query):
            token_from_db = manual_token or hash_sign(
                self.env, scope, (access_token_id, res_model, res_id, owner_id, json_extra and hashlib.sha256(json_extra.encode()).hexdigest()), expiration
            )
            if consteq(token, token_from_db):
                return self.env[model].browse(res_id).with_context(access_token_extra=json_extra and json.loads(json_extra))

        raise AccessError(self.env._("Invalid token: expired (revoked) or invalid."))


class Base(models.AbstractModel):
    _inherit = 'base'

    def _grant_access_token(
        self,
        scope: str,
        *,
        duration: timedelta | None = None,
        owner: BaseModel | None = None,
        extra: Any = None,
        _manual_token: str | None = None,
    ) -> str:
        """ Generate and get access token for the record. """
        assert owner is None or owner._name == 'res.users'

        self.ensure_one()
        return self.env['ir.access.token']._IrAccessToken__generate(
            self._name, self.id, scope,
            duration, owner.id if owner else None,
            extra,
            _manual_token,
        )

    @api.model
    def _get_sudo_record_from_access_token(
        self,
        scope: str,
        token: str,
        *,
        record: BaseModel | None = None
    ) -> BaseModel:
        """ Retrieve the sudoed record referenced by the token. """
        return self.env['ir.access.token']._IrAccessToken__retrieve_sudo_record(
            self._name, scope, token,
            res_model=record._name if record else None,
            res_id=record.id if record else None,
        )

    @api.model
    def _revoke_access_tokens(
        self,
        scope: str,
        *,
        owners: BaseModel | None = None,
        revoke_shared: bool = False,
    ) -> int:
        """ Ensures that tokens for the records and scope are invalidated.

        :param scope: access scope associated with the tokens.
        :param owners: if `res.users` records, delete access tokens for these users.
        :param revoke_shared: if `True`, delete shared access tokens (without user).
        :return: number of deleted access tokens.
        """
        assert owners is None or owners._name == 'res.users'
        assert self.env.su, "Sudo environment is required to revoke access tokens."

        domain = Domain([
            ('res_model', '=', self._name),
            ('res_id', 'in', self._ids),
            ('scope', '=', scope),
        ])

        owner_domain = Domain.FALSE
        if owners is not None:
            owner_domain |= Domain('owner_id', 'in', owners.ids)
        if revoke_shared:
            owner_domain |= Domain('owner_id', '=', False)
        if not owner_domain.is_false():
            domain &= owner_domain

        access_tokens = self.env['ir.access.token'].search(domain)
        if access_tokens:
            access_tokens.unlink()
            _logger.info("User %d revokes access tokens (%s)", self.env.uid, ', '.join(map(str, access_tokens._ids)))
        return len(access_tokens)
