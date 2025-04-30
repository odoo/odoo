import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ProductCatalogKanbanController.prototype, {
    _defineButtonContent() {
        super._defineButtonContent(...arguments);
        this.displaySuggestButton = (
            this.orderResModel === "purchase.order" && this.orderStateInfo.state === "draft"
        );
    },

    async openSuggestWizard() {
        // Display a warning if there is no product.
        const records = this.model.root.records.filter((rec) => !rec.productCatalogData.isSample);
        if (records.length === 0) {
            return this.dialog.add(ConfirmationDialog, {
                title: _t("No product to buy found"),
                body: _t("Change the applied filters to receive suggestions about quantities to replenish for desired products."),
            });
        }
        const args = [[this.orderId], this.model.config.domain];
        const action = await this.model.orm.call("purchase.order", "action_display_suggest", args);
        const onClose = (args) => {
            return args?.refresh && this._adaptSearchFilter();
        };
        this.actionService.doAction(action, { onClose });
    },

    _adaptSearchFilter() {
        // Add "In the Order" filter in the search bar if it wasn't already there.
        const { searchModel } = this.env.model.env;
        const inTheOrderFilter = Object.values(searchModel.searchItems).find(
            (searchItem) => searchItem.name === "products_in_purchase_order"
        );
        if (inTheOrderFilter &&
            searchModel.query.findIndex((queryEl) => queryEl.searchItemId === inTheOrderFilter.id) === -1
        ) {
            searchModel.toggleSearchItem(inTheOrderFilter.id);
        } else {
            this.model.load();
        }
    }
});
