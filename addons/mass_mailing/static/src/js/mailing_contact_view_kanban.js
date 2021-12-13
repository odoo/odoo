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
        this.do_action('mass_mailing.mailing_contact_import_action', {
            additional_context: this.renderer.state.context,
        });
    }
});

var MailingContactView = KanbanView.extend({
    config: Object.assign({}, KanbanView.prototype.config, {
        Controller: MailingContactController,
    }),
});

viewRegistry.add('mailing_contact_kanban', MailingContactView);
