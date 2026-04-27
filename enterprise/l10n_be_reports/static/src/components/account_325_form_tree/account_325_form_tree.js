/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

class Form325ListController extends ListController {
    create325Form() {
        this.actionService.doAction("l10n_be_reports.action_open_create_325_form");
    }
}

const Form325ListView = {
    ...listView,
    Controller: Form325ListController,
    buttonTemplate: "l10n_be_reports.form_325.ListView.buttons",
};

registry.category("views").add("account_325_form_tree", Form325ListView);
