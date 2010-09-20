# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
from osv import osv, fields
from tools.translate import _
import tools

def _generate_random_number():
   import random
   RANDOM_PASS_CHARACTERS = [chr(x) for x in range(48,58) + range(97,123) + range(65,91)]
   RANDOM_PASS_CHARACTERS.remove('l') #lowercase l, easily mistaken as one or capital i
   RANDOM_PASS_CHARACTERS.remove('I') #uppercase i, easily mistaken as one or lowercase l
   RANDOM_PASS_CHARACTERS.remove('O') #uppercase o, mistaken with zero
   RANDOM_PASS_CHARACTERS.remove('o') #lowercase o, mistaken with zero
   RANDOM_PASS_CHARACTERS.remove('0') #zero, mistaken with o-letter
   def generate_random_pass():
       pass_chars = RANDOM_PASS_CHARACTERS[:]
       random.shuffle(pass_chars)
       return ''.join(pass_chars[0:10])
   return generate_random_pass()

class share_create(osv.osv_memory):
    _name = 'share.create'
    _description = 'Create share'

    def _access(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        res = {}
        action_id = context.get('action_id', False)
        access_obj = self.pool.get('ir.model.access')
        action_obj = self.pool.get('ir.actions.act_window')
        model_obj = self.pool.get('ir.model')
        user_obj = self.pool.get('res.users')
        current_user = user_obj.browse(cr, uid, uid)
        access_ids = []
        if action_id:
            action = action_obj.browse(cr, uid, action_id, context=context)
            active_model_ids = model_obj.search(cr, uid, [('model','=',action.res_model)])
            active_model_id = active_model_ids and active_model_ids[0] or False
            access_ids = access_obj.search(cr, uid, [
                    ('group_id','in',map(lambda x:x.id, current_user.groups_id)),
                    ('model_id','',active_model_id)])
        for rec_id in ids:
            write_access = False
            read_access = False
            for access in access_obj.browse(cr, uid, access_ids, context=context):
                if access.perm_write:
                    write_access = True
                if access.perm_read:
                    read_access = True
            res[rec_id]['write_access'] = write_access
            res[rec_id]['read_access'] = read_access          
        return res

    _columns = {
        'action_id': fields.many2one('ir.actions.act_window', 'Action', required=True),
        'domain': fields.char('Domain', size=64),
        'user_type': fields.selection( [ ('existing','Existing'),('new','New')],'User Type'),
        'user_ids': fields.many2many('res.users', 'share_user_rel', 'share_id','user_id', 'Share Users'),
        'new_user': fields.text("New user"),
        'access_mode': fields.selection([('readwrite','READ & WRITE'),('readonly','READ ONLY')],'Access Mode'),
        'write_access': fields.function(_access, method=True, string='Write Access',type='boolean', multi='write_access'),
        'read_access': fields.function(_access, method=True, string='Write Access',type='boolean', multi='read_access'),
    }
    _defaults = {
        'user_type' : 'existing',
        'domain': '[]',
        'access_mode': 'readonly'

    }

    def default_get(self, cr, uid, fields, context=None):
        """
             To get default values for the object.
        """

        res = super(share_create, self).default_get(cr, uid, fields, context=context)
        if not context:
            context={}
        action_id = context.get('action_id', False)
        domain = context.get('domain', '[]')


        if 'action_id' in fields:
            res['action_id'] = action_id
        if 'domain' in fields:
            res['domain'] = domain
        return res

    def do_step_1(self, cr, uid, ids, context=None):
        """
        This action to excute step 1

        """
        if not context:
            context = {}

        data_obj = self.pool.get('ir.model.data')

        step1_form_view = data_obj._get_id(cr, uid, 'share', 'share_step1_form')

        if step1_form_view:
            step1_form_view_id = data_obj.browse(cr, uid, step1_form_view, context=context).res_id

        step1_id = False
        for this in self.browse(cr, uid, ids, context=context):
            vals ={
                'domain': this.domain,
                'action_id': this.action_id and this.action_id.id or False,
            }
            step1_id = this.id

        context.update(vals)
        value = {
            'name': _('Step:2 Sharing Wizard'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'share.create',
            'view_id': False,
            'res_id': step1_id,
            'views': [(step1_form_view_id, 'form'), (False, 'tree'), (False, 'calendar'), (False, 'graph')],
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new'
        }
        return value


    def do_step_2(self, cr, uid, ids, context=None):
        """
        This action to excute step 2

        """
        if not context:
            context = {}

        data_obj = self.pool.get('ir.model.data')

        step2_form_view = data_obj._get_id(cr, uid, 'share', 'share_step2_form')

        if step2_form_view:
            step2_form_view_id = data_obj.browse(cr, uid, step2_form_view, context=context).res_id

        step1_id = False
        for this in self.browse(cr, uid, ids, context=context):
            vals = {
                'user_type': this.user_type,
                'existing_user_ids': map(lambda x:x.id, this.user_ids),
                'new_user': this.new_user,
            }

        context.update(vals)
        value = {
            'name': _('Step:3 Sharing Wizard'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'share.create',
            'view_id': False,
            'views': [(step2_form_view_id, 'form'), (False, 'tree'), (False, 'calendar'), (False, 'graph')],
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new'
        }
        return value


    def do_step_3(self, cr, uid, ids, context=None):
        """
        This action to excute step 3

        """
        if not context:
            context = {}

        for this in self.browse(cr, uid, ids, context=context):
            vals = {
                'access_mode': this.access_mode,
            }

        context.update(vals)

        group_obj = self.pool.get('res.groups')
        user_obj = self.pool.get('res.users')
        fields_obj = self.pool.get('ir.model.fields')
        model_access_obj = self.pool.get('ir.model.access')
        model_obj = self.pool.get('ir.model')
        rule_obj = self.pool.get('ir.rule')
        action_obj = self.pool.get('ir.actions.act_window')

        new_users = context.get('new_user', False)
        action_id = context.get('action_id', False)
        user_type = context.get('user_type', False)
        access_mode = context.get('access_mode', False)
        action = action_obj.browse(cr, uid, action_id, context=context)
        active_model = action.res_model

        active_id = False #TODO: Pass record id of res_model of action
        existing_user_ids = context.get('existing_user_ids', False)
        domain = eval(context.get('domain', '[]'))

        # Create Share Group
        share_group_name = '%s: %s' %('Sharing', active_model)
        group_ids = group_obj.search(cr, uid, [('name','=',share_group_name)])
        group_id = group_ids and group_ids[0] or False
        if not group_id:
            group_id = group_obj.create(cr, uid, {'name': share_group_name, 'share': True})
        else:
            group = group_obj.browse(cr, uid, group_id, context=context)
            if not group.share:
                raise osv.except_osv(_('Error'), _("Share Group is exits without sharing !"))

        # Create new user

        current_user = user_obj.browse(cr, uid, uid)
        user_ids = []
        if user_type == 'new' and new_users:
            for new_user in new_users.split('\n'):
                password = _generate_random_number()
                user_id = user_obj.create(cr, uid, {
                        'login': new_user,
                        'password': password,
                        'name': new_user,
                        'user_email': new_user,
                        'groups_id': [(6,0,[group_id])],
                        'action_id': action_id,
                        'share': True,
                        'company_id': current_user.company_id and current_user.company_id.id
                })
                user_ids.append(user_id)
            context['new_user_ids'] = user_ids

        # Modify existing user
        if user_type == 'existing':
            user_obj.write(cr, uid, existing_user_ids , {
                                   'groups_id': [(4,group_id)],
                                   'action_id': action_id
                            })


        #ACCESS RIGHTS / IR.RULES COMPUTATION

        active_model_ids = model_obj.search(cr, uid, [('model','=',active_model)])
        active_model_id = active_model_ids and active_model_ids[0] or False

        def _get_relation(model_id, ttypes, new_obj=[]):
            obj = []
            models = map(lambda x:x[1].model, new_obj)
            field_ids = fields_obj.search(cr, uid, [('model_id','=',model_id),('ttype','in', ttypes)])
            for field in fields_obj.browse(cr, uid, field_ids, context=context):
                if field.relation not in models:
                    relation_model_ids = model_obj.search(cr, uid, [('model','=',field.relation)])
                    relation_model_id = relation_model_ids and relation_model_ids[0] or False
                    relation_model = model_obj.browse(cr, uid, relation_model_id, context=context)
                    obj.append((field.relation_field, relation_model))

                    if relation_model_id != model_id and field.ttype in ['one2many', 'many2many']:
                        obj += _get_relation(relation_model_id, [field.ttype], obj)

            return obj

        active_model = model_obj.browse(cr, uid, active_model_id, context=context)
        obj0 = [(None, active_model)]
        obj1 = _get_relation(active_model_id, ['one2many'])
        obj2 = _get_relation(active_model_id, ['one2many', 'many2many'])
        obj3 = _get_relation(active_model_id, ['many2one'])
        for rel_field, model in obj1:
            obj3 += _get_relation(model.id, ['many2one'])

        current_user = user_obj.browse(cr, uid, uid, context=context)
        if access_mode == 'readonly':
            res = []
            # intersect with read access rights of user running the
            # wizard, to avoid adding more access than current
            for group in current_user.groups_id:
                for access_control in group.model_access:
                     if access_control.model_id.id in res:
                        continue
                     if access_control.perm_read:
                        res.append(access_control.model_id.id)
                        model_access_obj.create(cr, uid, {
                        'name': 'Read Access of group %s on %s model'%(share_group_name, access_control.model_id.name),
                        'model_id' : access_control.model_id.id,
                        'group_id' : group_id,
                        'perm_read' : True
                        })
            res = []
            for rel_field, model in obj0+obj1+obj2+obj3:
                if model.id in res:
                    continue
                res.append(model.id)
                model_access_obj.create(cr, uid, {
                    'name': 'Read Access of group %s on %s model'%(share_group_name, model.name),
                    'model_id' : model.id,
                    'group_id' : group_id,
                    'perm_read' : True
                })
        if access_mode == 'readwrite':
            res = []
            for rel_field, model in obj0+obj1:
                if model.id in res:
                    continue
                res.append(model.id)
                model_access_obj.create(cr, uid, {
                    'name': 'Write Access of group %s on %s model'%(share_group_name, model.name),
                    'model_id' : model.id,
                    'group_id' : group_id,
                    'perm_read' : True,
                    'perm_write' : True,
                    'perm_unlink' : True,
                    'perm_create' : True,
                })
            # intersect with access rights of user
            # running the wizard, to avoid adding more access than current

            for group in current_user.groups_id:
                for access_control in group.model_access:
                     if access_control.model_id.id in res:
                        continue
                     if access_control.perm_read:
                        res.append(access_control.model_id.id)
                        model_access_obj.create(cr, uid, {
                            'name': 'Read Access of group %s on %s model'%(share_group_name, access_control.model_id.name),
                            'model_id' : access_control.model_id.id,
                            'group_id' : group_id,
                            'perm_read' : True
                        })
            for rel_field, model in obj2+obj3:
                if model.id in res:
                    continue
                res.append(model.id)
                model_access_obj.create(cr, uid, {
                            'name': 'Read Access of group %s on %s model'%(share_group_name, model.name),
                            'model_id' : model.id,
                            'group_id' : group_id,
                            'perm_read' : True
                        })
        #
        # And on OBJ0, OBJ1, OBJ2, OBJ3: add all rules from groups of the user
        #  that is sharing in the many2many of the rules on the new group
        #  (rule must be copied instead of adding it if it contains a reference to uid
        #  or user.xxx so it can be replaced correctly)

        for group in current_user.groups_id:
            res = []
            for rel_field, model in obj0+obj1+obj2+obj3:
                if model.id in res:
                    continue
                res.append(model.id)
                for rule in group.rule_groups:
                    if rule.model_id == model.id:
                        rule_obj.copy(cr, uid, rule.id, default={
                            'name': '%s-%s'%(share_group_name, model.model),
                            'groups': [(6,0,[group_id])]
                        }, context=context)

        rule_obj.create(cr, uid, {
                'name': '%s-%s'%(share_group_name, active_model.model),
                'model_id': active_model.id,
                'domain_force': domain,
                'groups': [(6,0,[group_id])]
            })
        for rel_field, model in obj1:
            obj1_domain = []
            for opr1, opt, opr2 in domain:
                new_opr1 = '%s.%s'%(rel_field, opr1)
                obj1_domain.append((new_opr1, opt, opr2))

            rule_obj.create(cr, uid, {
                'name': '%s-%s'%(share_group_name, model.model),
                'model_id': model.id,
                'domain_force': obj1_domain,
                'groups': [(6,0,[group_id])]
            })
        context['share_model'] = active_model.model
        context['share_rec_id'] = active_id


        data_obj = self.pool.get('ir.model.data')

        form_view = data_obj._get_id(cr, uid, 'share', 'share_result_form')
        form_view_id = False
        if form_view:
            form_view_id = data_obj.browse(cr, uid, form_view, context=context).res_id


        value = {
            'name': _('Step:4 Share Users Detail'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'share.result',
            'view_id': False,
            'views': [(form_view_id, 'form'), (False, 'tree'), (False, 'calendar'), (False, 'graph')],
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new'
        }
        return value
share_create()


class share_result(osv.osv_memory):
    _name = "share.result"
    _columns = {
        'users': fields.text("Users", readonly=True),
     }



    def do_send_email(self, cr, uid, ids, context=None):
        user_obj = self.pool.get('res.users')
        if not context:
            context={}
        existing_user_ids = context.get('existing_user_ids', [])
        new_user_ids = context.get('new_user_ids', [])
        share_url = tools.config.get('share_root_url', False)
        user = user_obj.browse(cr, uid, uid, context=context)
        for share_user in user_obj.browse(cr, uid, new_user_ids+existing_user_ids, context=context):
            email_to = share_user.user_email
            subject = '%s wants to share private data with you' %(user.name)
            body = """
    Dear,

             %s wants to share private data from OpenERP with you!
    """%(user.name)
            if share_url:
                body += """
             To view it, you can access the following URL:
                   %s
    """%(user.name, share_url)
            if share_user.id in new_user_ids:
                body += """
             You may use the following login and password to get access to this
             protected area:
                   login: %s
                   password: %s
    """%(user.login, user.password)
            elif share_user.id in existing_user_ids:
                 body += """
             You may use your existing login and password to get access to this
             additional data. As a reminder, your login is %s.
    """%(user.name)

            flag = tools.email_send(
                user.user_email,
                email_to,
                subject,
                body
            )
        return flag


    def default_get(self, cr, uid, fields, context=None):
        """
             To get default values for the object.
        """

        res = super(share_result, self).default_get(cr, uid, fields, context=context)
        user_obj = self.pool.get('res.users')
        if not context:
            context={}
        existing_user_ids = context.get('existing_user_ids', [])
        new_user_ids = context.get('new_user_ids', [])
        share_url = tools.config.get('share_root_url', False)
        if 'users' in fields:
            users = []
            for user in user_obj.browse(cr, uid, new_user_ids):
                txt = 'Login: %s Password: %s' %(user.login, user.password)
                if share_url:
                    txt += ' Share URL: %s' %(share_url)
                users.append(txt)
            for user in user_obj.browse(cr, uid, existing_user_ids):
                txt = 'Login: %s' %(user.login)
                if share_url:
                    txt += ' Share URL: %s' %(share_url)
                users.append(txt)
            res['users'] = '\n'.join(users)
        return res

share_result()
