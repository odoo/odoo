import { onWillDestroy } from "@odoo/owl";
import { SWITCHSIGN, DECIMAL } from "@point_of_sale/app/components/numpad/numpad";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useBus } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";

patch(ProductScreen.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.state.tableBuffer = "";
        this.state.isValidBuffer = true;
        this.doSubmitOrder = useTrackedAsync(() => this.pos.submitOrder());
        this.doReprintOrder = useTrackedAsync(() => this.pos.reprintOrder());
        useBus(this.numberBuffer, "buffer-update", ({ detail: value }) => {
            this.checkIsValid(value);
        });

        onWillDestroy(() => {
            this.pos.numpadMode = "quantity";
        });
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
