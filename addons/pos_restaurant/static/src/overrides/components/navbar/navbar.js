import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { TipScreen } from "@pos_restaurant/app/tip_screen/tip_screen";
import { patch } from "@web/core/utils/patch";
import { ListContainer } from "@point_of_sale/app/generic_components/list_container/list_container";
import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";
import { _t } from "@web/core/l10n/translation";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import {
    getButtons,
    DECIMAL,
    ZERO,
    BACKSPACE,
} from "@point_of_sale/app/generic_components/numpad/numpad";

patch(Navbar, {
    components: { ...Navbar.components, ListContainer },
});
patch(Navbar.prototype, {
    async onClickBackButton() {
        if (this.pos.orderToTransferUuid) {
            const order = this.pos.models["pos.order"].getBy("uuid", this.pos.orderToTransferUuid);
            this.pos.set_order(order);
            if (order.table_id) {
                this.pos.setTable(order.table_id);
            }
            this.pos.orderToTransferUuid = false;
            this.pos.showScreen("ProductScreen");
            return;
        }
        if (this.pos.mainScreen.component && this.pos.config.module_pos_restaurant) {
            if (
                (this.pos.mainScreen.component === ProductScreen &&
                    this.pos.mobile_pane == "right") ||
                this.pos.mainScreen.component === TipScreen
            ) {
                this.pos.showScreen("FloorScreen", { floor: this.floor });
            } else {
                super.onClickBackButton(...arguments);
            }
            return;
        }
        super.onClickBackButton(...arguments);
    },
    /**
     * If no table is set to pos, which means the current main screen
     * is floor screen, then the order count should be based on all the orders.
     */

    get orderCount() {
        if (this.pos.config.module_pos_restaurant && this.pos.selectedTable) {
            return this.pos.getTableOrders(this.pos.selectedTable.id).length;
        }
        return super.orderCount;
    },
    getTable() {
        return this.pos.orderToTransferUuid
            ? this.pos.models["pos.order"].find((o) => o.uuid == this.pos.orderToTransferUuid)
                  ?.table_id
            : this.pos.selectedTable;
    },
    get showTableIcon() {
        return typeof this.getTable()?.table_number === "number" && this.pos.showBackButton();
    },
    onSwitchButtonClick() {
        const mode = this.pos.floorPlanStyle === "kanban" ? "default" : "kanban";
        localStorage.setItem("floorPlanStyle", mode);
        this.pos.floorPlanStyle = mode;
    },
    newFloatingOrder() {
        this.pos.add_new_order();
        this.pos.showScreen("ProductScreen");
    },
    getFloatingOrders() {
        return this.pos.get_open_orders().filter((order) => !order.table_id);
    },
    selectFloatingOrder(order) {
        this.pos.set_order(order);
        this.pos.showScreen("ProductScreen");
    },
    editOrderNote(order) {
        this.dialog.add(TextInputPopup, {
            title: _t("Edit order note"),
            placeholder: _t("Emma's Birthday Party"),
            startingValue: order.note,
            getPayload: async (newName) => {
                if (typeof order.id == "number") {
                    this.pos.data.write("pos.order", [order.id], {
                        note: newName,
                    });
                } else {
                    order.note = newName;
                }
            },
        });
    },
    get showEditPlanButton() {
        return true;
    },
    async switchTable() {
        const table_number = await makeAwaitable(this.dialog, NumberPopup, {
            title: _t("Table Selector"),
            placeholder: _t("Enter a table number"),
            buttons: getButtons([{ ...DECIMAL, disabled: true }, ZERO, BACKSPACE]),
            defaultPayload: { value: null },
        });
        if (!table_number) {
            return;
        }
        const find_table = (t) => t.table_number === parseInt(table_number);
        let table = this.pos.currentFloor?.table_ids.find(find_table);
        if (!table) {
            table = this.pos.models["restaurant.table"].find(find_table);
        }
        let floating_order;
        if (!table) {
            floating_order = this.getFloatingOrders().find(
                (o) => o.getFloatingOrderName() === table_number
            );
        }
        if (!table && !floating_order) {
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t("No table or floating order found with this number"),
            });
            return;
        }
        this.pos.selectedTable = null;
        this.pos.searchProductWord = "";
        if (table) {
            await this.pos.setTableFromUi(table);
        } else {
            this.selectFloatingOrder(floating_order);
        }
    },
});
