/** @odoo-module */
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";

export class PurchaseDashBoard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        onWillStart(async () => {
            this.purchaseData = await this.orm.call("purchase.order", "retrieve_dashboard");
        });
    }

    /**
     * This method clears the current search query and activates
     * the filters found in `filter_name` attibute from button pressed
     */
    setSearchContext(ev) {
        const filter_name = ev.currentTarget.getAttribute("filter_name");
        const filters = filter_name.split(",");
        const searchItems = this.env.searchModel.getSearchItems((item) =>
            filters.includes(item.name)
        );
        this.env.searchModel.query = [];
        for (const item of searchItems) {
            this.env.searchModel.toggleSearchItem(item.id);
        }
    }
}

PurchaseDashBoard.template = "purchase.PurchaseDashboard";
