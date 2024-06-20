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
import { ActionScreen } from "@point_of_sale/app/screens/action_screen";

patch(Navbar, {
    components: { ...Navbar.components, ListContainer },
});
patch(Navbar.prototype, {
    async onClickBackButton() {
        if (this.pos.orderToTransferUuid) {
            const order = this.pos.models["pos.order"].getBy("uuid", this.pos.orderToTransferUuid);
            this.pos.set_order(order);
            if (order.table_id) {
                await this.pos.setTable(order.table_id);
            }
            this.pos.orderToTransferUuid = false;
            this.pos.showScreen("ProductScreen");
            return;
        }
        if (this.pos.mainScreen.component && this.pos.config.module_pos_restaurant) {
            if (
                (this.pos.mainScreen.component === ProductScreen &&
                    this.pos.mobile_pane == "right") ||
                this.pos.mainScreen.component === TipScreen ||
                this.pos.mainScreen.component === ActionScreen
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
        return this.getTable()?.name && this.pos.showBackButton();
    },
    getTableName() {
        const table = this.getTable();
        const child_tables = this.pos.models["restaurant.table"].filter((t) => {
            if (t.floor_id.id === table.floor_id.id) {
                return table.isParent(t);
            }
        });
        let name = table.name;
        for (const child_table of child_tables) {
            name += ` & ${child_table.name}`;
        }
        return name;
    },
    onSwitchButtonClick() {
        const mode = this.pos.floorPlanStyle === "kanban" ? "default" : "kanban";
        localStorage.setItem("floorPlanStyle", mode);
        this.pos.floorPlanStyle = mode;
    },
    newFloatingOrder() {
        const order = this.pos.add_new_order();
        order.setBooked(true);
        this.pos.showScreen("ProductScreen");
    },
    getFloatingOrders() {
        return this.pos
            .get_open_orders()
            .filter((order) => !order.table_id)
            .sort((a, b) => {
                const noteA = a.note || "";
                const noteB = b.note || "";
                if (noteA && noteB) {
                    // Both have notes
                    const timePattern = /^\d{1,2}:\d{2}/;

                    const aMatch = noteA.match(timePattern);
                    const bMatch = noteB.match(timePattern);

                    if (aMatch && bMatch) {
                        // Both have times, compare by time
                        const aTime = aMatch[0];
                        const bTime = bMatch[0];
                        // add padding to make sure the time is always 4 characters long
                        // such that, for example, 9:45 does not come after 10:00
                        const [aHour, aMinute] = aTime.split(":");
                        const [bHour, bMinute] = bTime.split(":");
                        const formattedATime = aHour.padStart(2, "0") + aMinute.padStart(2, "0");
                        const formattedBTime = bHour.padStart(2, "0") + bMinute.padStart(2, "0");
                        return formattedATime.localeCompare(formattedBTime);
                    } else if ((aMatch && !bMatch) || (bMatch && !aMatch)) {
                        // One has time, the other does not
                        return bMatch ? -1 : 1;
                    }
                    // Neither have times, compare by note
                    return noteA.localeCompare(noteB);
                } else if (noteA || noteB) {
                    // a has note, b does not
                    return noteA ? -1 : 1;
                } else {
                    // Neither have notes, compare by tracking number
                    return a.tracking_number > b.tracking_number ? 1 : -1;
                }
            });
    },
    selectFloatingOrder(order) {
        this.pos.set_order(order);
        this.pos.showScreen("ProductScreen");
    },
    editOrderNote(order) {
        this.dialog.add(TextInputPopup, {
            title: _t("Edit order name"),
            placeholder: _t("18:45 John 4P"),
            startingValue: order.note || "",
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
        });
        if (!table_number) {
            return;
        }
        const find_table = (t) => t.name === table_number;
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
        await this.pos.syncAllOrders();
        if (table) {
            await this.pos.setTableFromUi(table);
        } else {
            this.selectFloatingOrder(floating_order);
        }
    },
});
