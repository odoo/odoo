/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { listView } from '@web/views/list/list_view';
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";

/**
 * List view for the <mailing.contact> model.
 *
 * Add an import button to open the wizard <mailing.contact.import>. This wizard
 * allows the user to import contacts line by line.
 */
export class MailingContactListController extends ListController {
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

registry.category('views').add('mailing_contact_list', {
    ...listView,
    Controller: MailingContactListController,
    buttonTemplate: 'MailingContactListView.buttons',
}); 
