# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import consteq


def validate_thread_with_hash_pid(thread, _hash, pid):
    if not _hash or not pid:
        return False
    pid = int(pid)
    if consteq(_hash, thread._sign_token(pid)):
        return True
    parent_sign_token = thread._portal_get_parent_hash_token(pid)
    return parent_sign_token and consteq(_hash, parent_sign_token)


def validate_thread_with_token(thread, token):
    return token and consteq(token, thread[thread._mail_post_token_field])


def get_portal_partner(thread, _hash, pid, token):
    if validate_thread_with_hash_pid(thread, _hash, pid):
        return thread.env["res.partner"].sudo().browse(int(pid))
    if validate_thread_with_token(thread, token):
        if partner := thread._mail_get_partners()[thread.id][:1]:
            return partner
    return thread.env["res.partner"]
