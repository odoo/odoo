# Notice:
# ------
#
# Implements encrypting functions.
#
# Copyright (c) 2008, F S 3 Consulting Inc.
#
# Maintainer:
# Alec Joseph Rivera (agi<at>fs3.ph)
#
#
# Warning:
# -------
#
# This program as  such is intended to be used by  professional programmers
# who take the whole responsibility of assessing all potential consequences
# resulting  from its eventual  inadequacies and  bugs.  End users  who are
# looking  for a  ready-to-use  solution  with  commercial  guarantees  and
# support are strongly adviced to contract a Free Software Service Company.
#
# This program  is Free Software; you can  redistribute it and/or modify it
# under  the terms of the  GNU General  Public License  as published by the
# Free Software  Foundation;  either version 2 of the  License, or (at your
# option) any later version.
#
# This  program is  distributed in  the hope that  it will  be useful,  but
# WITHOUT   ANY   WARRANTY;   without   even   the   implied   warranty  of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should  have received a copy of the GNU General  Public License along
# with this program; if not, write to the:
#
# Free Software Foundation, Inc.
# 59 Temple Place - Suite 330
# Boston, MA  02111-1307
# USA.

from random import seed, sample
from string import ascii_letters, digits
from osv import fields,osv
import pooler
from tools.translate import _
from service import security

magic_md5 = '$1$'

def gen_salt( length=8, symbols=ascii_letters + digits ):
    seed()
    return ''.join( sample( symbols, length ) )

# The encrypt_md5 is based on Mark Johnson's md5crypt.py, which in turn is
# based on  FreeBSD src/lib/libcrypt/crypt.c (1.2)  by  Poul-Henning Kamp.
# Mark's port can be found in  ActiveState ASPN Python Cookbook.  Kudos to
# Poul and Mark. -agi
#
# Original license:
#
# * "THE BEER-WARE LICENSE" (Revision 42):
# *
# * <phk@login.dknet.dk>  wrote  this file.  As  long as  you retain  this
# * notice  you can do  whatever you want with this stuff. If we meet some
# * day,  and you think this stuff is worth it,  you can buy me  a beer in
# * return.
# *
# * Poul-Henning Kamp


#TODO: py>=2.6: from hashlib import md5
import hashlib

def encrypt_md5( raw_pw, salt, magic=magic_md5 ):
    raw_pw = raw_pw.encode('utf-8')
    salt = salt.encode('utf-8')
    hash = hashlib.md5()
    hash.update( raw_pw + magic + salt )
    st = hashlib.md5()
    st.update( raw_pw + salt + raw_pw)
    stretch = st.digest()

    for i in range( 0, len( raw_pw ) ):
        hash.update( stretch[i % 16] )

    i = len( raw_pw )

    while i:
        if i & 1:
            hash.update('\x00')
        else:
            hash.update( raw_pw[0] )
        i >>= 1

    saltedmd5 = hash.digest()

    for i in range( 1000 ):
        hash = hashlib.md5()

        if i & 1:
            hash.update( raw_pw )
        else:
            hash.update( saltedmd5 )

        if i % 3:
            hash.update( salt )
        if i % 7:
            hash.update( raw_pw )
        if i & 1:
            hash.update( saltedmd5 )
        else:
            hash.update( raw_pw )

        saltedmd5 = hash.digest()

    itoa64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

    rearranged = ''
    for a, b, c in ((0, 6, 12), (1, 7, 13), (2, 8, 14), (3, 9, 15), (4, 10, 5)):
        v = ord( saltedmd5[a] ) << 16 | ord( saltedmd5[b] ) << 8 | ord( saltedmd5[c] )

        for i in range(4):
            rearranged += itoa64[v & 0x3f]
            v >>= 6

    v = ord( saltedmd5[11] )

    for i in range( 2 ):
        rearranged += itoa64[v & 0x3f]
        v >>= 6

    return magic + salt + '$' + rearranged

class users(osv.osv):
    _name="res.users"
    _inherit="res.users"
    # agi - 022108
    # Add handlers for 'input_pw' field.

    def set_pw(self, cr, uid, id, name, value, args, context):
        if not value:
            raise osv.except_osv(_('Error'), _("Please specify the password !"))

        obj = pooler.get_pool(cr.dbname).get('res.users')
        if not hasattr(obj, "_salt_cache"):
            obj._salt_cache = {}

        salt = obj._salt_cache[id] = gen_salt()
        encrypted = encrypt_md5(value, salt)
        cr.execute('update res_users set password=%s where id=%s',
            (encrypted.encode('utf-8'), int(id)))
        cr.commit()
        del value

    def get_pw( self, cr, uid, ids, name, args, context ):
        cr.execute('select id, password from res_users where id in %s', (tuple(map(int, ids)),))
        stored_pws = cr.fetchall()
        res = {}

        for id, stored_pw in stored_pws:
            res[id] = stored_pw

        return res

    _columns = {
        # The column size could be smaller as it is meant to store a hash, but
        # an existing column cannot be downsized; thus we use the original
        # column size.
        'password': fields.function(get_pw, fnct_inv=set_pw, type='char',
            size=64, string='Password', invisible=True,
            store=True),
    }

    def login(self, db, login, password):
        if not password:
            return False
        if db is False:
            raise RuntimeError("Cannot authenticate to False db!")
        cr = None
        try:
            cr = pooler.get_db(db).cursor()
            return self._login(cr, db, login, password)
        except Exception:
            import logging
            logging.getLogger('netsvc').exception('Could not authenticate')
            return Exception('Access Denied')
        finally:
            if cr is not None:
                cr.close()

    def _login(self, cr, db, login, password):
        cr.execute( 'SELECT password, id FROM res_users WHERE login=%s AND active',
            (login.encode('utf-8'),))

        if cr.rowcount:
            stored_pw, id = cr.fetchone()
        else:
            # Return early if no one has a login name like that.
            return False
    
        stored_pw = self.maybe_encrypt(cr, stored_pw, id)
        
        if not stored_pw:
            # means couldn't encrypt or user is not active!
            return False

        # Calculate an encrypted password from the user-provided
        # password.
        obj = pooler.get_pool(db).get('res.users')
        if not hasattr(obj, "_salt_cache"):
            obj._salt_cache = {}
        salt = obj._salt_cache[id] = stored_pw[len(magic_md5):11]
        encrypted_pw = encrypt_md5(password, salt)
    
        # Check if the encrypted password matches against the one in the db.
        cr.execute("""UPDATE res_users
                        SET date=now() AT TIME ZONE 'UTC'
                        WHERE id=%s AND password=%s AND active
                        RETURNING id""", 
                   (int(id), encrypted_pw.encode('utf-8')))
        res = cr.fetchone()
        cr.commit()
    
        if res:
            return res[0]
        else:
            return False

    def check(self, db, uid, passwd):
        if not passwd:
            # empty passwords disallowed for obvious security reasons
            raise security.ExceptionNoTb('AccessDenied')

        # Get a chance to hash all passwords in db before using the uid_cache.
        obj = pooler.get_pool(db).get('res.users')
        if not hasattr(obj, "_salt_cache"):
            obj._salt_cache = {}
            self._uid_cache.get(db, {}).clear()

        cached_pass = self._uid_cache.get(db, {}).get(uid)
        if (cached_pass is not None) and cached_pass == passwd:
            return True

        cr = pooler.get_db(db).cursor()
        try:
            if uid not in self._salt_cache.get(db, {}):
                # If we don't have cache, we have to repeat the procedure
                # through the login function.
                cr.execute( 'SELECT login FROM res_users WHERE id=%s', (uid,) )
                stored_login = cr.fetchone()
                if stored_login:
                    stored_login = stored_login[0]
        
                res = self._login(cr, db, stored_login, passwd)
                if not res:
                    raise security.ExceptionNoTb('AccessDenied')
            else:
                salt = self._salt_cache[db][uid]
                cr.execute('SELECT COUNT(*) FROM res_users WHERE id=%s AND password=%s AND active', 
                    (int(uid), encrypt_md5(passwd, salt)))
                res = cr.fetchone()[0]
        finally:
            cr.close()

        if not bool(res):
            raise security.ExceptionNoTb('AccessDenied')

        if res:
            if self._uid_cache.has_key(db):
                ulist = self._uid_cache[db]
                ulist[uid] = passwd
            else:
                self._uid_cache[db] = {uid: passwd}
        return bool(res)
    
    def maybe_encrypt(self, cr, pw, id):
        """ Return the password 'pw', making sure it is encrypted.
        
        If the password 'pw' is not encrypted, then encrypt all active passwords
        in the db. Returns the (possibly newly) encrypted password for 'id'.
        """

        if not pw.startswith(magic_md5):
            cr.execute("SELECT id, password FROM res_users " \
                "WHERE active=true AND password NOT LIKE '$%'")
            # Note that we skip all passwords like $.., in anticipation for
            # more than md5 magic prefixes.
            res = cr.fetchall()
            for i, p in res:
                encrypted = encrypt_md5(p, gen_salt())
                cr.execute('UPDATE res_users SET password=%s where id=%s',
                        (encrypted, i))
                if i == id:
                    encrypted_res = encrypted
            cr.commit()
            return encrypted_res
        return pw

users()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
