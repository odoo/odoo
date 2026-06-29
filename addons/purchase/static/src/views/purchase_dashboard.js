import { asyncComputed, Component, computed, onWillStart, plugin } from "@odoo/owl";
import { ORM } from "@web/core/orm_plugin";

export class PurchaseDashBoard extends Component {
    static template = "purchase.PurchaseDashboard";
    static props = { list: { type: Object, optional: true } };

    orm = plugin(ORM);

    purchaseData = asyncComputed(() => {
        this.props.list;
        return this.orm.call("purchase.order", "retrieve_dashboard");
    });

    multiuser = computed(
        () => JSON.stringify(this.purchaseData().global) !== JSON.stringify(this.purchaseData().my)
    );

    setup() {
        onWillStart(async () => {
            await this.purchaseData.currentPromise();
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
