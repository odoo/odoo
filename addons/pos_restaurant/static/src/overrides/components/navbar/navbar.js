import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import {
    getButtons,
    EMPTY,
    ZERO,
    BACKSPACE,
} from "@point_of_sale/app/generic_components/numpad/numpad";
import { TableSelector } from "./table_selector/table_selector";

patch(Navbar.prototype, {
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
<<<<<<< master
    showTabs() {
        if (this.pos.config.module_pos_restaurant) {
            return !this.pos.selectedTable;
        } else {
            return super.showTabs();
        }
    },
||||||| 6bbb977d3a1bee6e1ded52f0a90a089440b4d3c6
    getTable() {
        return this.pos.orderToTransferUuid
            ? this.pos.models["pos.order"].find((o) => o.uuid == this.pos.orderToTransferUuid)
                  ?.table_id
            : this.pos.selectedTable;
    },
    showTabs() {
        if (this.pos.config.module_pos_restaurant) {
            return !(this.pos.selectedTable || this.pos.orderToTransferUuid);
        } else {
            return super.showTabs();
        }
    },
=======
>>>>>>> d23b553b089245c6b395dbb6e0aa72ebb4cd3203
    onSwitchButtonClick() {
        const mode = this.pos.floorPlanStyle === "kanban" ? "default" : "kanban";
        localStorage.setItem("floorPlanStyle", mode);
        this.pos.floorPlanStyle = mode;
    },
    get showEditPlanButton() {
        return true;
    },
    setFloatingOrder(floatingOrder) {
        this.pos.selectedTable = null;
        this.pos.set_order(floatingOrder);

        const props = {};
        const screenName = floatingOrder.get_screen_data().name;
        if (screenName === "PaymentScreen") {
            props.orderUuid = floatingOrder.uuid;
        }

        this.pos.showScreen(screenName || "ProductScreen", props);
    },
    async onClickTableTab() {
        await this.pos.syncAllOrders();
        this.dialog.add(TableSelector, {
            title: _t("Table Selector"),
            placeholder: _t("Enter a table number"),
            buttons: getButtons([
                EMPTY,
                ZERO,
                { ...BACKSPACE, class: "o_colorlist_item_color_transparent_1" },
            ]),
            confirmButtonLabel: _t("Jump to table"),
            getPayload: async (table_number) => {
                const find_table = (t) => t.table_number === parseInt(table_number);
                const table =
                    this.pos.currentFloor?.table_ids.find(find_table) ||
                    this.pos.models["restaurant.table"].find(find_table);
                if (table) {
                    return this.pos.setTableFromUi(table);
                }
                const floating_order = this.pos
                    .get_open_orders()
                    .find((o) => o.getFloatingOrderName() === table_number);
                if (floating_order) {
                    return this.setFloatingOrder(floating_order);
                }
                if (!table && !floating_order) {
                    this.dialog.add(AlertDialog, {
                        title: _t("Error"),
                        body: _t("No table or floating order found with this number"),
                    });
                    return;
                }
            },
        });
    },
    onClickPlanButton() {
        this.pos.showScreen("FloorScreen", { floor: this.floor });
    },
});
