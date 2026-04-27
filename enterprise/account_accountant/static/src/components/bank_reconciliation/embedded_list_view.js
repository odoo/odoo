/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

export class BankRecEmbeddedListController extends ListController {
    /** Remove the Export Cog **/
    static template = "account_accountant.BankRecEmbeddedListController";
}


export class BankRecWidgetFormEmbeddedListModel extends listView.Model {
    setup(params, { action, dialog, notification, rpc, user, view, company }) {
        super.setup(...arguments);
        this.storedDomainString = null;
    }

    /**
    * @override
    * the list of AMLs don't need to be fetched from the server every time the form view is re-rendered.
    * this disables the retrieval, while still ensuring that the search bar works.
    */
    async load(params = {}) {
        const currentDomain = params.domain.toString();
        if (currentDomain !== this.storedDomainString) {
            this.storedDomainString = currentDomain;
            return super.load(params);
        }
    }
}

export const EmbeddedListView = {
    ...listView,
    Controller: BankRecEmbeddedListController,
    Model: BankRecWidgetFormEmbeddedListModel,
};
