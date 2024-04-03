/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { kanbanView } from '@web/views/kanban/kanban_view';
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";

export class MailingContactController extends KanbanController {
    async setup() {
        super.setup();
        this.actionService = useService("action");
    }

    onImport() {
        const context = this.props.context;
        const actionParams = { additionalContext: context };
        if (!context.default_mailing_list_ids && context.active_model === 'mailing.list' && context.active_ids) {
            actionParams.additionalContext.default_mailing_list_ids = context.active_ids;
        }
        this.actionService.doAction('mass_mailing.mailing_contact_import_action', actionParams);
    }
};

registry.category('views').add('mailing_contact_kanban', {
    ...kanbanView,
    Controller: MailingContactController,
    buttonTemplate: 'MailingContactKanbanView.buttons',
}); 
