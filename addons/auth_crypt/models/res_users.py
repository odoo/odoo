# -*- coding: utf-8 -*-

import logging
from passlib.context import CryptContext

import odoo
from odoo import api, fields, models

from odoo.addons.base.res import res_users
res_users.USER_PRIVATE_FIELDS.append('password_crypt')

_logger = logging.getLogger(__name__)

default_crypt_context = CryptContext(
    # kdf which can be verified by the context. The default encryption kdf is
    # the first of the list
    ['pbkdf2_sha512', 'md5_crypt'],
    # deprecated algorithms are still verified as usual, but ``needs_update``
    # will indicate that the stored hash should be replaced by a more recent
    # algorithm. Passlib 1.6 supports an `auto` value which deprecates any
    # algorithm but the default, but Ubuntu LTS only provides 1.5 so far.
    deprecated=['md5_crypt'],
)


class ResUsers(models.Model):
    _inherit = "res.users"

    def init(self):
        _logger.info("Hashing passwords, may be slow for databases with many users...")
        self.env.cr.execute("SELECT id, password FROM res_users"
                   " WHERE password IS NOT NULL"
                   "   AND password != ''")
        for uid, pwd in self.env.cr.fetchall():
            self.sudo().browse(uid)._set_password(pwd)

    password = fields.Char(compute='_compute_password', inverse='_inverse_password', invisible=True, store=True)
    password_crypt = fields.Char(string='Encrypted Password', invisible=True, copy=False)

    def _compute_password(self):
        self.env.cr.execute('SELECT id, password FROM res_users WHERE id IN %s', [tuple(self.ids)])
        password_dict = dict(self.env.cr.fetchall())
        for user in self:
            user.password = password_dict[user.id]

    def _inverse_password(self):
        for user in self:
            user._set_password(user.password)
            self.invalidate_cache()

    @api.model
    def check_credentials(self, password):
        # convert to base_crypt if needed
        self.env.cr.execute('SELECT password, password_crypt FROM res_users WHERE id=%s AND active', (self.env.uid,))
        encrypted = None
        user = self.env.user
        if self.env.cr.rowcount:
            stored, encrypted = self.env.cr.fetchone()
            if stored and not encrypted:
                user._set_password(stored)
                self.invalidate_cache()
        try:
            return super(ResUsers, self).check_credentials(password)
        except odoo.exceptions.AccessDenied:
            if encrypted:
                valid_pass, replacement = user._crypt_context()\
                        .verify_and_update(password, encrypted)
                if replacement is not None:
                    user._set_encrypted_password(replacement)
                if valid_pass:
                    return
            raise

    def _set_password(self, password):
        self.ensure_one()
        """ Encrypts then stores the provided plaintext password for the user
        ``self``
        """
        encrypted = self._crypt_context().encrypt(password)
        self._set_encrypted_password(encrypted)

    def _set_encrypted_password(self, encrypted):
        """ Store the provided encrypted password to the database, and clears
        any plaintext password
        """
        self.env.cr.execute(
            "UPDATE res_users SET password='', password_crypt=%s WHERE id=%s",
            (encrypted, self.id))

    def _crypt_context(self):
        """ Passlib CryptContext instance used to encrypt and verify
        passwords. Can be overridden if technical, legal or political matters
        require different kdfs than the provided default.

        Requires a CryptContext as deprecation and upgrade notices are used
        internally
        """
        return default_crypt_context
