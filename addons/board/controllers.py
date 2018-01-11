# -*- coding: utf-8 -*-
from xml.etree import ElementTree

from openerp.addons.web.controllers.main import load_actions_from_ir_values
from openerp.http import Controller, route, request

class Board(Controller):
    @route('/board/add_to_dashboard', type='json', auth='user')
    def add_to_dashboard(self, menu_id, action_id, context_to_save, domain, view_mode, name=''):
        # FIXME move this method to board.board model
        dashboard_action = load_actions_from_ir_values('action', 'tree_but_open',
                                                       [('ir.ui.menu', menu_id)], False)

        if dashboard_action:
            action = dashboard_action[0][2]
            if action['res_model'] == 'board.board' and action['views'][0][1] == 'form':
                # Maybe should check the content instead of model board.board ?
                view_id = action['views'][0][0]
                board = request.session.model(action['res_model']).fields_view_get(view_id, 'form')
                if board and 'arch' in board:
                    xml = ElementTree.fromstring(board['arch'])
                    column = xml.find('./board/column')
                    if column is not None:
                        new_action = ElementTree.Element('action', {
                            'name': str(action_id),
                            'string': name,
                            'view_mode': view_mode,
                            'context': str(context_to_save),
                            'domain': str(domain)
                        })
                        column.insert(0, new_action)
                        arch = ElementTree.tostring(xml, 'utf-8')
                        return request.session.model('ir.ui.view.custom').create({
                            'user_id': request.session.uid,
                            'ref_id': view_id,
                            'arch': arch
                        }, request.context)

        return False
