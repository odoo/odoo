import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";

export class PurchaseDashBoard extends Component {
    static template = "purchase.PurchaseDashboard";
    static props = { list: { type: Object, optional: true } };
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        onWillStart(async () => {
            await this.updateDashboardState();
        });
        onWillUpdateProps(async () => {
            await this.updateDashboardState();
        });
    }
    async updateDashboardState() {
        this.purchaseData = await this.orm.call("purchase.order", "retrieve_dashboard");
        this.multiuser = JSON.stringify(this.purchaseData.global) !== JSON.stringify(this.purchaseData.my);
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
