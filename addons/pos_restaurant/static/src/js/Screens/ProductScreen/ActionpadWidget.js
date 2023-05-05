/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { ActionpadWidget } from "@point_of_sale/js/Screens/ProductScreen/ActionpadWidget";
/**
 * @props partner
 */

patch(ActionpadWidget.prototype, "point_of_sale.ActionpadWidget", {
    get swapButton() {
        return (
            String.prototype.valueOf.call(this.props.actionName) === "Payment" &&
            this.pos.globalState.config.module_pos_restaurant &&
            this.pos.globalState.printers_category_ids_set.size
        );
    },
    get currentOrder() {
        return this.pos.globalState.get_order();
    },
    get addedClasses() {
        if (!this.currentOrder) {
            return {};
        }
        const hasChanges = this.currentOrder.hasChangesToPrint();
        const skipped = hasChanges ? false : this.currentOrder.hasSkippedChanges();
        return {
            highlight: hasChanges,
            altlight: skipped,
        };
    },
    async submitOrder() {
        if (!this.clicked) {
            this.clicked = true;
            try {
                this.currentOrder.submitOrder();
            } finally {
                this.clicked = false;
            }
        }
    },
    get highlightPay() {
        return (
            this._super(...arguments) &&
            this.pos.globalState.printers_category_ids_set.size &&
            !this.currentOrder.hasChangesToPrint()
        );
    },
});
