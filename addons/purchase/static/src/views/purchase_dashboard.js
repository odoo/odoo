import { Component, onWillStart, plugin, proxy } from "@odoo/owl";
import { ORM } from "@web/core/orm_plugin";

export class PurchaseDashBoard extends Component {
    static template = "purchase.PurchaseDashboard";

    orm = plugin(ORM);

    setup() {
        this.state = proxy({
            purchaseData: {},
            multiuser: false,
        });
        onWillStart(async () => {
            const update = (data) => {
                this.state.purchaseData = data;
                this.state.multiuser = JSON.stringify(data.global) !== JSON.stringify(data.my);
            };
            const cache = {
                type: "disk",
                update: "always",
                callback(freshData, hasChanged) {
                    if (hasChanged) {
                        update(freshData);
                    }
                },
            };
            const data = await this.orm.cache(cache).call("purchase.order", "retrieve_dashboard");
            update(data);
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
