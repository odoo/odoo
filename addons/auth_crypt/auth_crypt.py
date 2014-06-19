import logging

from passlib.context import CryptContext

import openerp
from openerp.osv import fields, osv

_logger = logging.getLogger(__name__)

default_crypt_context = CryptContext(
    # kdf which can be verified by the context. The default encryption kdf is
    # the first of the list
    ['pbkdf2_sha512', 'md5_crypt'],
    # deprecated algorithms are still verified as usual, but ``needs_update``
    # will indicate that the stored hash should be replaced by a more recent
    # algorithm. Passlib 1.6 supports an `auto` value which deprecates any
    # algorithm but the default, but Debian only provides 1.5 so...
    deprecated=['md5_crypt'],
)

class res_users(osv.osv):
    _inherit = "res.users"

    def init(self, cr):
        _logger.info("Hashing passwords, may be slow for databases with many users...")
        cr.execute("SELECT id, password FROM res_users"
                   " WHERE password IS NOT NULL"
                   "   AND password != ''")
        for uid, pwd in cr.fetchall():
            self._set_password(cr, openerp.SUPERUSER_ID, uid, pwd)

    def set_pw(self, cr, uid, id, name, value, args, context):
        if value:
            self._set_password(cr, uid, id, value, context=context)

    def get_pw( self, cr, uid, ids, name, args, context ):
        cr.execute('select id, password from res_users where id in %s', (tuple(map(int, ids)),))
        return dict(cr.fetchall())

    _columns = {
        'password': fields.function(get_pw, fnct_inv=set_pw, type='char', string='Password', invisible=True, store=True),
        'password_crypt': fields.char(string='Encrypted Password', invisible=True),
    }

    def check_credentials(self, cr, uid, password):
        # convert to base_crypt if needed
        cr.execute('SELECT password, password_crypt FROM res_users WHERE id=%s AND active', (uid,))
        encrypted = None
        if cr.rowcount:
            stored, encrypted = cr.fetchone()
            if stored and not encrypted:
                self._set_password(cr, uid, uid, stored)
        try:
            return super(res_users, self).check_credentials(cr, uid, password)
        except openerp.exceptions.AccessDenied:
            if encrypted:
                valid_pass, replacement = self._crypt_context(cr, uid, uid)\
                        .verify_and_update(password, encrypted)
                if replacement is not None:
                    self._set_encrypted_password(cr, uid, uid, replacement)
                if valid_pass:
                    return

            raise

    def _set_password(self, cr, uid, id, password, context=None):
        """ Encrypts then stores the provided plaintext password for the user
        ``id``
        """
        encrypted = self._crypt_context(cr, uid, id, context=context).encrypt(password)
        self._set_encrypted_password(cr, uid, id, encrypted, context=context)

    def _set_encrypted_password(self, cr, uid, id, encrypted, context=None):
        """ Store the provided encrypted password to the database, and clears
        any plaintext password

        :param uid: id of the current user
        :param id: id of the user on which the password should be set
        """
        cr.execute(
            "UPDATE res_users SET password='', password_crypt=%s WHERE id=%s",
            (encrypted, id))

    def _crypt_context(self, cr, uid, id, context=None):
        """ Passlib CryptContext instance used to encrypt and verify
        passwords. Can be overridden if technical, legal or political matters
        require different kdfs than the provided default.

        Requires a CryptContext as deprecation and upgrade notices are used
        internally
        """
        return default_crypt_context


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
