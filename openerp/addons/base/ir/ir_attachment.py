# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import hashlib
import itertools
import logging
import os
import re

from openerp import tools
from openerp.tools.translate import _
from openerp.exceptions import AccessError
from openerp.osv import fields,osv
from openerp import SUPERUSER_ID
from openerp.osv.orm import except_orm
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

class ir_attachment(osv.osv):
    """Attachments are used to link binary files or url to any openerp document.

    External attachment storage
    ---------------------------
    
    The 'data' function field (_data_get,data_set) is implemented using
    _file_read, _file_write and _file_delete which can be overridden to
    implement other storage engines, shuch methods should check for other
    location pseudo uri (example: hdfs://hadoppserver)
    
    The default implementation is the file:dirname location that stores files
    on the local filesystem using name based on their sha1 hash
    """
    _order = 'id desc'
    def _name_get_resname(self, cr, uid, ids, object, method, context):
        data = {}
        for attachment in self.browse(cr, uid, ids, context=context):
            model_object = attachment.res_model
            res_id = attachment.res_id
            if model_object and res_id:
                model_pool = self.pool[model_object]
                res = model_pool.name_get(cr,uid,[res_id],context)
                res_name = res and res[0][1] or None
                if res_name:
                    field = self._columns.get('res_name',False)
                    if field and len(res_name) > field.size:
                        res_name = res_name[:30] + '...' 
                data[attachment.id] = res_name or False
            else:
                data[attachment.id] = False
        return data

    def _storage(self, cr, uid, context=None):
        return self.pool['ir.config_parameter'].get_param(cr, SUPERUSER_ID, 'ir_attachment.location', 'file')

    def _filestore(self, cr, uid, context=None):
        return tools.config.filestore(cr.dbname)

    def force_storage(self, cr, uid, context=None):
        """Force all attachments to be stored in the currently configured storage"""
        if not self.pool['res.users'].has_group(cr, uid, 'base.group_erp_manager'):
            raise AccessError(_('Only administrators can execute this action.'))

        location = self._storage(cr, uid, context)
        domain = {
            'db': [('store_fname', '!=', False)],
            'file': [('db_datas', '!=', False)],
        }[location]

        ids = self.search(cr, uid, domain, context=context)
        for attach in self.browse(cr, uid, ids, context=context):
            attach.write({'datas': attach.datas})
        return True

    # 'data' field implementation
    def _full_path(self, cr, uid, path):
        # sanitize ath
        path = re.sub('[.]', '', path)
        path = path.strip('/\\')
        return os.path.join(self._filestore(cr, uid), path)

    def _get_path(self, cr, uid, bin_data):
        sha = hashlib.sha1(bin_data).hexdigest()

        # retro compatibility
        fname = sha[:3] + '/' + sha
        full_path = self._full_path(cr, uid, fname)
        if os.path.isfile(full_path):
            return fname, full_path        # keep existing path

        # scatter files across 256 dirs
        # we use '/' in the db (even on windows)
        fname = sha[:2] + '/' + sha
        full_path = self._full_path(cr, uid, fname)
        dirname = os.path.dirname(full_path)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        return fname, full_path

    def _file_read(self, cr, uid, fname, bin_size=False):
        full_path = self._full_path(cr, uid, fname)
        r = ''
        try:
            if bin_size:
                r = os.path.getsize(full_path)
            else:
                r = open(full_path,'rb').read().encode('base64')
        except IOError:
            _logger.exception("_read_file reading %s", full_path)
        return r

    def _file_write(self, cr, uid, value):
        bin_value = value.decode('base64')
        fname, full_path = self._get_path(cr, uid, bin_value)
        if not os.path.exists(full_path):
            try:
                with open(full_path, 'wb') as fp:
                    fp.write(bin_value)
            except IOError:
                _logger.exception("_file_write writing %s", full_path)
        return fname

    def _file_delete(self, cr, uid, fname):
        # using SQL to include files hidden through unlink or due to record rules
        cr.execute("SELECT COUNT(*) FROM ir_attachment WHERE store_fname = %s", (fname,))
        count = cr.fetchone()[0]
        full_path = self._full_path(cr, uid, fname)
        if not count and os.path.exists(full_path):
            try:
                os.unlink(full_path)
            except OSError:
                _logger.exception("_file_delete could not unlink %s", full_path)
            except IOError:
                # Harmless and needed for race conditions
                _logger.exception("_file_delete could not unlink %s", full_path)

    def _data_get(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        result = {}
        bin_size = context.get('bin_size')
        for attach in self.browse(cr, uid, ids, context=context):
            if attach.store_fname:
                result[attach.id] = self._file_read(cr, uid, attach.store_fname, bin_size)
            else:
                result[attach.id] = attach.db_datas
        return result

    def _data_set(self, cr, uid, id, name, value, arg, context=None):
        # We dont handle setting data to null
        if not value:
            return True
        if context is None:
            context = {}
        location = self._storage(cr, uid, context)
        file_size = len(value.decode('base64'))
        attach = self.browse(cr, uid, id, context=context)
        fname_to_delete = attach.store_fname
        if location != 'db':
            fname = self._file_write(cr, uid, value)
            # SUPERUSER_ID as probably don't have write access, trigger during create
            super(ir_attachment, self).write(cr, SUPERUSER_ID, [id], {'store_fname': fname, 'file_size': file_size, 'db_datas': False}, context=context)
        else:
            super(ir_attachment, self).write(cr, SUPERUSER_ID, [id], {'db_datas': value, 'file_size': file_size, 'store_fname': False}, context=context)

        # After de-referencing the file in the database, check whether we need
        # to garbage-collect it on the filesystem
        if fname_to_delete:
            self._file_delete(cr, uid, fname_to_delete)
        return True

    _name = 'ir.attachment'
    _columns = {
        'name': fields.char('Attachment Name', required=True),
        'datas_fname': fields.char('File Name'),
        'description': fields.text('Description'),
        'res_name': fields.function(_name_get_resname, type='char', string='Resource Name', store=True),
        'res_model': fields.char('Resource Model', readonly=True, help="The database object this attachment will be attached to"),
        'res_id': fields.integer('Resource ID', readonly=True, help="The record id this is attached to"),
        'create_date': fields.datetime('Date Created', readonly=True),
        'create_uid':  fields.many2one('res.users', 'Owner', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', change_default=True),
        'type': fields.selection( [ ('url','URL'), ('binary','Binary'), ],
                'Type', help="Binary File or URL", required=True, change_default=True),
        'url': fields.char('Url', size=1024),
        # al: We keep shitty field names for backward compatibility with document
        'datas': fields.function(_data_get, fnct_inv=_data_set, string='File Content', type="binary", nodrop=True),
        'store_fname': fields.char('Stored Filename'),
        'db_datas': fields.binary('Database Data'),
        'file_size': fields.integer('File Size'),
    }

    _defaults = {
        'type': 'binary',
        'file_size': 0,
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'ir.attachment', context=c),
    }

    def _auto_init(self, cr, context=None):
        super(ir_attachment, self)._auto_init(cr, context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('ir_attachment_res_idx',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX ir_attachment_res_idx ON ir_attachment (res_model, res_id)')
            cr.commit()

    def check(self, cr, uid, ids, mode, context=None, values=None):
        """Restricts the access to an ir.attachment, according to referred model
        In the 'document' module, it is overriden to relax this hard rule, since
        more complex ones apply there.
        """
        res_ids = {}
        require_employee = False
        if ids:
            if isinstance(ids, (int, long)):
                ids = [ids]
            cr.execute('SELECT DISTINCT res_model, res_id, create_uid FROM ir_attachment WHERE id = ANY (%s)', (ids,))
            for rmod, rid, create_uid in cr.fetchall():
                if not (rmod and rid):
                    if create_uid != uid:
                        require_employee = True
                    continue
                res_ids.setdefault(rmod,set()).add(rid)
        if values:
            if values.get('res_model') and values.get('res_id'):
                res_ids.setdefault(values['res_model'],set()).add(values['res_id'])

        ima = self.pool.get('ir.model.access')
        for model, mids in res_ids.items():
            # ignore attachments that are not attached to a resource anymore when checking access rights
            # (resource was deleted but attachment was not)
            if not self.pool.get(model):
                require_employee = True
                continue
            existing_ids = self.pool[model].exists(cr, uid, mids)
            if len(existing_ids) != len(mids):
                require_employee = True
            ima.check(cr, uid, model, mode)
            self.pool[model].check_access_rule(cr, uid, existing_ids, mode, context=context)
        if require_employee:
            if not uid == SUPERUSER_ID and not self.pool['res.users'].has_group(cr, uid, 'base.group_user'):
                raise except_orm(_('Access Denied'), _("Sorry, you are not allowed to access this document."))

    def _search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False, access_rights_uid=None):
        ids = super(ir_attachment, self)._search(cr, uid, args, offset=offset,
                                                 limit=limit, order=order,
                                                 context=context, count=False,
                                                 access_rights_uid=access_rights_uid)
        if not ids:
            if count:
                return 0
            return []

        # Work with a set, as list.remove() is prohibitive for large lists of documents
        # (takes 20+ seconds on a db with 100k docs during search_count()!)
        orig_ids = ids
        ids = set(ids)

        # For attachments, the permissions of the document they are attached to
        # apply, so we must remove attachments for which the user cannot access
        # the linked document.
        # Use pure SQL rather than read() as it is about 50% faster for large dbs (100k+ docs),
        # and the permissions are checked in super() and below anyway.
        cr.execute("""SELECT id, res_model, res_id FROM ir_attachment WHERE id = ANY(%s)""", (list(ids),))
        targets = cr.dictfetchall()
        model_attachments = {}
        for target_dict in targets:
            if not target_dict['res_model']:
                continue
            # model_attachments = { 'model': { 'res_id': [id1,id2] } }
            model_attachments.setdefault(target_dict['res_model'],{}).setdefault(target_dict['res_id'] or 0, set()).add(target_dict['id'])

        # To avoid multiple queries for each attachment found, checks are
        # performed in batch as much as possible.
        ima = self.pool.get('ir.model.access')
        for model, targets in model_attachments.iteritems():
            if model not in self.pool:
                continue
            if not ima.check(cr, uid, model, 'read', False):
                # remove all corresponding attachment ids
                for attach_id in itertools.chain(*targets.values()):
                    ids.remove(attach_id)
                continue # skip ir.rule processing, these ones are out already

            # filter ids according to what access rules permit
            target_ids = targets.keys()
            allowed_ids = [0] + self.pool[model].search(cr, uid, [('id', 'in', target_ids)], context=context)
            disallowed_ids = set(target_ids).difference(allowed_ids)
            for res_id in disallowed_ids:
                for attach_id in targets[res_id]:
                    ids.remove(attach_id)

        # sort result according to the original sort ordering
        result = [id for id in orig_ids if id in ids]
        return len(result) if count else list(result)

    def read(self, cr, uid, ids, fields_to_read=None, context=None, load='_classic_read'):
        if isinstance(ids, (int, long)):
            ids = [ids]
        self.check(cr, uid, ids, 'read', context=context)
        return super(ir_attachment, self).read(cr, uid, ids, fields_to_read, context=context, load=load)

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        self.check(cr, uid, ids, 'write', context=context, values=vals)
        if 'file_size' in vals:
            del vals['file_size']
        return super(ir_attachment, self).write(cr, uid, ids, vals, context)

    def copy(self, cr, uid, id, default=None, context=None):
        self.check(cr, uid, [id], 'write', context=context)
        return super(ir_attachment, self).copy(cr, uid, id, default, context)

    def unlink(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        self.check(cr, uid, ids, 'unlink', context=context)

        # First delete in the database, *then* in the filesystem if the
        # database allowed it. Helps avoid errors when concurrent transactions
        # are deleting the same file, and some of the transactions are
        # rolled back by PostgreSQL (due to concurrent updates detection).
        to_delete = [a.store_fname
                        for a in self.browse(cr, uid, ids, context=context)
                            if a.store_fname]
        res = super(ir_attachment, self).unlink(cr, uid, ids, context)
        for file_path in to_delete:
            self._file_delete(cr, uid, file_path)

        return res

    def create(self, cr, uid, values, context=None):
        self.check(cr, uid, [], mode='write', context=context, values=values)
        if 'file_size' in values:
            del values['file_size']
        return super(ir_attachment, self).create(cr, uid, values, context)

    def action_get(self, cr, uid, context=None):
        return self.pool.get('ir.actions.act_window').for_xml_id(
            cr, uid, 'base', 'action_attachment', context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
