/** @odoo-module **/

import KanbanController from 'web.KanbanController';
import KanbanView from 'web.KanbanView';
import viewRegistry from 'web.view_registry';

var MailingContactController = KanbanController.extend({
    buttons_template: 'MailingContactKanbanView.buttons',

    events: Object.assign({}, KanbanController.prototype.events, {
        'click .o_mass_mailing_import_contact': '_onImport',
    }),

    _onImport() {
        const context = this.renderer.state.context || {};
        const actionParams = { additional_context: context };
        if (!context.default_mailing_list_ids && context.active_model === 'mailing.list' && context.active_ids) {
            actionParams.additional_context.default_mailing_list_ids = context.active_ids;
        }
        this.do_action('mass_mailing.mailing_contact_import_action', actionParams);
    }
});

var MailingContactView = KanbanView.extend({
    config: Object.assign({}, KanbanView.prototype.config, {
        Controller: MailingContactController,
    }),
});

viewRegistry.add('mailing_contact_kanban', MailingContactView);
