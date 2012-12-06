# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2012 OpenERP s.a. (<http://openerp.com>).
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

""" Helper functions for reports testing.

    Please /do not/ import this file by default, but only explicitly call it
    through the code of yaml tests.
"""

import openerp.netsvc as netsvc
import openerp.tools as tools
import logging
import openerp.pooler as pooler
from openerp.tools.safe_eval import safe_eval
from subprocess import Popen, PIPE
import os
import tempfile

_logger = logging.getLogger(__name__)

def try_report(cr, uid, rname, ids, data=None, context=None, our_module=None):
    """ Try to render a report <rname> with contents of ids
    
        This function should also check for common pitfalls of reports.
    """
    if data is None:
        data = {}
    if context is None:
        context = {}
    if rname.startswith('report.'):
        rname_s = rname[7:]
    else:
        rname_s = rname
    _logger.log(netsvc.logging.TEST, "  - Trying %s.create(%r)", rname, ids)
    res = netsvc.LocalService(rname).create(cr, uid, ids, data, context)
    if not isinstance(res, tuple):
        raise RuntimeError("Result of %s.create() should be a (data,format) tuple, now it is a %s" % \
                                (rname, type(res)))
    (res_data, res_format) = res

    if not res_data:
        raise ValueError("Report %s produced an empty result!" % rname)

    if tools.config['test_report_directory']:
        file(os.path.join(tools.config['test_report_directory'], rname+ '.'+res_format), 'wb+').write(res_data)

    _logger.debug("Have a %s report for %s, will examine it", res_format, rname)
    if res_format == 'pdf':
        if res_data[:5] != '%PDF-':
            raise ValueError("Report %s produced a non-pdf header, %r" % (rname, res_data[:10]))

        res_text = False
        try:
            fd, rfname = tempfile.mkstemp(suffix=res_format)
            os.write(fd, res_data)
            os.close(fd)

            proc = Popen(['pdftotext', '-enc', 'UTF-8', '-nopgbrk', rfname, '-'], shell=False, stdout=PIPE)
            stdout, stderr = proc.communicate()
            res_text = tools.ustr(stdout)
            os.unlink(rfname)
        except Exception:
            _logger.debug("Unable to parse PDF report: install pdftotext to perform automated tests.")

        if res_text is not False:
            for line in res_text.split('\n'):
                if ('[[' in line) or ('[ [' in line):
                    _logger.error("Report %s may have bad expression near: \"%s\".", rname, line[80:])
            # TODO more checks, what else can be a sign of a faulty report?
    elif res_format == 'foobar':
        # TODO
        pass
    else:
        _logger.warning("Report %s produced a \"%s\" chunk, cannot examine it", rname, res_format)
        return False

    _logger.log(netsvc.logging.TEST, "  + Report %s produced correctly.", rname)
    return True

def try_report_action(cr, uid, action_id, active_model=None, active_ids=None,
                wiz_data=None, wiz_buttons=None,
                context=None, our_module=None):
    """Take an ir.action.act_window and follow it until a report is produced

        :param action_id: the integer id of an action, or a reference to xml id
                of the act_window (can search [our_module.]+xml_id
        :param active_model, active_ids: call the action as if it had been launched
                from that model+ids (tree/form view action)
        :param wiz_data: a dictionary of values to use in the wizard, if needed.
                They will override (or complete) the default values of the
                wizard form.
        :param wiz_buttons: a list of button names, or button icon strings, which
                should be preferred to press during the wizard.
                Eg. 'OK' or 'gtk-print'
        :param our_module: the name of the calling module (string), like 'account'
    """

    if not our_module and isinstance(action_id, basestring):
        if '.' in action_id:
            our_module = action_id.split('.', 1)[0]

    if context is None:
        context = {}
    else:
        context = context.copy() # keep it local
    # TODO context fill-up

    pool = pooler.get_pool(cr.dbname)

    def log_test(msg, *args):
        _logger.log(netsvc.logging.TEST, "  - " + msg, *args)

    datas = {}
    if active_model:
        datas['model'] = active_model
    if active_ids:
        datas['ids'] = active_ids

    if not wiz_buttons:
        wiz_buttons = []

    if isinstance(action_id, basestring):
        if '.' in action_id:
            act_module, act_xmlid = action_id.split('.', 1)
        else:
            if not our_module:
                raise ValueError('You cannot only specify action_id "%s" without a module name' % action_id)
            act_module = our_module
            act_xmlid = action_id
        act_model, act_id = pool.get('ir.model.data').get_object_reference(cr, uid, act_module, act_xmlid)
    else:
        assert isinstance(action_id, (long, int))
        act_model = 'ir.action.act_window'     # assume that
        act_id = action_id
        act_xmlid = '<%s>' % act_id

    def _exec_action(action, datas, context):
        # taken from client/modules/action/main.py:84 _exec_action()
        if isinstance(action, bool) or 'type' not in action:
            return
        # Updating the context : Adding the context of action in order to use it on Views called from buttons
        if datas.get('id',False):
            context.update( {'active_id': datas.get('id',False), 'active_ids': datas.get('ids',[]), 'active_model': datas.get('model',False)})
        context.update(safe_eval(action.get('context','{}'), context.copy()))
        if action['type'] in ['ir.actions.act_window', 'ir.actions.submenu']:
            for key in ('res_id', 'res_model', 'view_type', 'view_mode',
                    'limit', 'auto_refresh', 'search_view', 'auto_search', 'search_view_id'):
                datas[key] = action.get(key, datas.get(key, None))

            view_id = False
            if action.get('views', []):
                if isinstance(action['views'],list):
                    view_id = action['views'][0][0]
                    datas['view_mode']= action['views'][0][1]
                else:
                    if action.get('view_id', False):
                        view_id = action['view_id'][0]
            elif action.get('view_id', False):
                view_id = action['view_id'][0]

            assert datas['res_model'], "Cannot use the view without a model"
            # Here, we have a view that we need to emulate
            log_test("will emulate a %s view: %s#%s",
                        action['view_type'], datas['res_model'], view_id or '?')

            view_res = pool.get(datas['res_model']).fields_view_get(cr, uid, view_id, action['view_type'], context)
            assert view_res and view_res.get('arch'), "Did not return any arch for the view"
            view_data = {}
            if view_res.get('fields',{}).keys():
                view_data = pool.get(datas['res_model']).default_get(cr, uid, view_res['fields'].keys(), context)
            if datas.get('form'):
                view_data.update(datas.get('form'))
            if wiz_data:
                view_data.update(wiz_data)
            _logger.debug("View data is: %r", view_data)

            for fk, field in view_res.get('fields',{}).items():
                # Default fields returns list of int, while at create()
                # we need to send a [(6,0,[int,..])]
                if field['type'] in ('one2many', 'many2many') \
                        and view_data.get(fk, False) \
                        and isinstance(view_data[fk], list) \
                        and not isinstance(view_data[fk][0], tuple) :
                    view_data[fk] = [(6, 0, view_data[fk])]

            action_name = action.get('name')
            try:
                from xml.dom import minidom
                cancel_found = False
                buttons = []
                dom_doc = minidom.parseString(view_res['arch'])
                if not action_name:
                    action_name = dom_doc.documentElement.getAttribute('name')

                for button in dom_doc.getElementsByTagName('button'):
                    button_weight = 0
                    if button.getAttribute('special') == 'cancel':
                        cancel_found = True
                        continue
                    if button.getAttribute('icon') == 'gtk-cancel':
                        cancel_found = True
                        continue
                    if button.getAttribute('default_focus') == '1':
                        button_weight += 20
                    if button.getAttribute('string') in wiz_buttons:
                        button_weight += 30
                    elif button.getAttribute('icon') in wiz_buttons:
                        button_weight += 10
                    string = button.getAttribute('string') or '?%s' % len(buttons)

                    buttons.append( { 'name': button.getAttribute('name'),
                                'string': string,
                                'type': button.getAttribute('type'),
                                'weight': button_weight,
                                })
            except Exception, e:
                _logger.warning("Cannot resolve the view arch and locate the buttons!", exc_info=True)
                raise AssertionError(e.args[0])

            if not datas['res_id']:
                # it is probably an orm_memory object, we need to create
                # an instance
                datas['res_id'] = pool.get(datas['res_model']).create(cr, uid, view_data, context)

            if not buttons:
                raise AssertionError("view form doesn't have any buttons to press!")

            buttons.sort(key=lambda b: b['weight'])
            _logger.debug('Buttons are: %s', ', '.join([ '%s: %d' % (b['string'], b['weight']) for b in buttons]))

            res = None
            while buttons and not res:
                b = buttons.pop()
                log_test("in the \"%s\" form, I will press the \"%s\" button.", action_name, b['string'])
                if not b['type']:
                    log_test("the \"%s\" button has no type, cannot use it", b['string'])
                    continue
                if b['type'] == 'object':
                    #there we are! press the button!
                    fn =  getattr(pool.get(datas['res_model']), b['name'])
                    if not fn:
                        _logger.error("The %s model doesn't have a %s attribute!", datas['res_model'], b['name'])
                        continue
                    res = fn(cr, uid, [datas['res_id'],], context)
                    break
                else:
                    _logger.warning("in the \"%s\" form, the \"%s\" button has unknown type %s",
                        action_name, b['string'], b['type'])
            return res

        elif action['type']=='ir.actions.report.xml':
            if 'window' in datas:
                del datas['window']
            if not datas:
                datas = action.get('datas',{})
            datas = datas.copy()
            ids = datas.get('ids')
            if 'ids' in datas:
                del datas['ids']
            res = try_report(cr, uid, 'report.'+action['report_name'], ids, datas, context, our_module=our_module)
            return res
        else:
            raise Exception("Cannot handle action of type %s" % act_model)

    log_test("will be using %s action %s #%d", act_model, act_xmlid, act_id)
    action = pool.get(act_model).read(cr, uid, act_id, context=context)
    assert action, "Could not read action %s[%s]" %(act_model, act_id)
    loop = 0
    while action:
        loop += 1
        # This part tries to emulate the loop of the Gtk client
        if loop > 100:
            _logger.error("Passed %d loops, giving up", loop)
            raise Exception("Too many loops at action")
        log_test("it is an %s action at loop #%d", action.get('type', 'unknown'), loop)
        result = _exec_action(action, datas, context)
        if not isinstance(result, dict):
            break
        datas = result.get('datas', {})
        if datas:
            del result['datas']
        action = result

    return True

#eof

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
