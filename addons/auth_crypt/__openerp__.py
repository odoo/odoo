# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Password Encryption',
    'version': '2.0',
    'author': ['Odoo SA', 'FS3'],
    'maintainer': 'OpenERP SA',
    'category': 'Tools',
    'description': """
Encrypted passwords
===================

Replaces the default password storage with a strong cryptographic
hash.

The key derivation function currently used is RSA Security LLC's
industry-standard ``PKDF2``, in combination with ``SHA512``.
This includes salting and key stretching with several thousands
rounds.

All passwords are encrypted as soon as the module is installed.
This may take a few minutes if there are thousands of users.

Past versions of encrypted passwords will be automatically upgraded
to the current scheme whenever a user authenticates
(``auth_crypt`` was previously using the weaker ``md5crypt`` key
derivation function).

Note: Installing this module permanently prevents user password
recovery and cannot be undone. It is thus recommended to enable
some password reset mechanism for users, such as the one provided
by the ``auth_signup`` module (signup for new users does not
necessarily have to be enabled).

""",
    'depends': ['base'],
    'data': [],
    'auto_install': True,
    'installable': True,
}
