import { onWillDestroy } from "@odoo/owl";
import { SWITCHSIGN, DECIMAL } from "@point_of_sale/app/components/numpad/numpad";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useBus } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.state.tableBuffer = "";
        this.state.isValidBuffer = true;
        useBus(this.numberBuffer, "buffer-update", ({ detail: value }) => {
            this.checkIsValid(value);
        });

        onWillDestroy(() => {
            this.pos.numpadMode = "quantity";
        });
    },
    get selectedOrderlineQuantity() {
        const order = this.pos.getOrder();
        const orderline = order.getSelectedOrderline();
        const isForPreparation = orderline.product_id.pos_categ_ids
            .map((categ) => categ.id)
            .some((id) => this.pos.config.preparationCategories.has(id));
        if (
            this.pos.config.module_pos_restaurant &&
            this.pos.config.preparationCategories.size &&
            isForPreparation
        ) {
            const changes = Object.values(this.pos.getOrderChanges().orderlines).find(
                (change) => change.name == orderline.getFullProductName()
            );
            return changes ? changes.quantity : false;
        }
        return super.selectedOrderlineQuantity;
    },
    get nbrOfChanges() {
        return this.pos.getOrderChanges().nbrOfChanges;
    },
    get swapButton() {
        return this.pos.config.module_pos_restaurant && this.pos.config.preparationCategories.size;
    },
    get displayCategoryCount() {
        return this.pos.categoryCount.slice(0, 3);
    },
    async submitOrder() {
        await this.pos.sendOrderInPreparationUpdateLastChange(this.currentOrder);
        this.pos.addPendingOrder([this.currentOrder.id]);
        this.pos.showScreen(this.pos.defaultScreen, {}, this.pos.defaultScreen == "ProductScreen");
    },
    get primaryReviewButton() {
        return (
            this.pos.config.module_pos_restaurant &&
            ((!this.pos.getOrder().isEmpty() && !this.primaryOrderButton) ||
                this.pos.getOrder().isDirectSale)
        );
    },
    get primaryOrderButton() {
        return (
            this.pos.getOrderChanges().nbrOfChanges !== 0 && this.pos.config.module_pos_restaurant
        );
    },
    getNumpadButtons() {
        let buttons = super.getNumpadButtons();
        if (this.pos.numpadMode === "table") {
            const toDisable = ["quantity", "discount", "price", SWITCHSIGN.value, DECIMAL.value];
            buttons = buttons.map((button) => ({
                ...button,
                class: `
                    ${button.class}
                    ${toDisable.includes(button.value) ? "disabled" : ""}
                `,
            }));
        }
        return buttons;
    },
    onNumpadClick(buttonValue) {
        super.onNumpadClick(buttonValue);
    },
    setTable() {
        this.pos.numpadMode = "table";
        this.numberBuffer.reset();
    },
    assignOrder() {
        if (this.state.isValidBuffer) {
            this.pos.searchOrder(this.state.tableBuffer);
            this.numberBuffer.reset();
            this.pos.numpadMode = "quantity";
        }
    },
    checkIsValid(buffer) {
        this.state.tableBuffer = buffer;
        const res = this.pos.findTable(buffer);
        this.state.isValidBuffer = Boolean(res);
    },
});
