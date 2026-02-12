import { Component, useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { OrderWidget } from "@pos_self_order/app/components/order_widget/order_widget";
import { PresetInfoPopup } from "@pos_self_order/app/components/preset_info_popup/preset_info_popup";
import { useScrollShadow } from "../../utils/scroll_shadow_hook";
import { CancelPopup } from "@pos_self_order/app/components/cancel_popup/cancel_popup";
import { _t } from "@web/core/l10n/translation";
import { formatProductName } from "../../utils";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { PillsSelectionPopup } from "@pos_self_order/app/components/pills_selection_popup/pills_selection_popup";

const { DateTime } = luxon;

export class CartPage extends Component {
    static template = "pos_self_order.CartPage";
    static components = { OrderWidget };
    static props = {};

    setup() {
        this.selfOrder = useSelfOrder();
        this.dialog = useService("dialog");
        this.router = useService("router");
        this.state = useState({
            showOrderNote: this.orderNote,
            orderNoteValue: "",
        });

        this.scrollShadow = useScrollShadow(useRef("scrollContainer"));
        this.renderer = useService("renderer");
    }

    get showCancelButton() {
        return (
            this.selfOrder.config.self_ordering_mode === "mobile" &&
            this.selfOrder.config.self_ordering_pay_after === "each" &&
            this.selfOrder.currentOrder.isSynced
        );
    }

    get orderNote() {
        return this.selfOrder?.currentOrder?.general_customer_note || this.state?.orderNoteValue;
    }

    get lines() {
        const selfOrder = this.selfOrder;
        const order = selfOrder.currentOrder;
        const lines =
            (selfOrder.config.self_ordering_pay_after === "meal" &&
            Object.keys(order.changes).length > 0
                ? order.unsentLines
                : this.selfOrder.currentOrder.lines) || [];

        return lines.filter((line) => !line.combo_parent_id);
    }

    get totalPriceAndTax() {
        const { amountTaxes, priceIncl } = this.selfOrder.currentOrder;
        const { priceWithTax, tax, count } = this.selfOrder.orderLineNotSend;
        return {
            priceWithTax: count > 0 ? priceWithTax : priceIncl,
            tax: count > 0 ? tax : amountTaxes,
        };
    }

    get optionalProducts() {
        const optionalProducts =
            this.selfOrder.currentOrder.lines.flatMap(
                (line) => line.product_id.product_tmpl_id.pos_optional_product_ids
            ) || [];
        return optionalProducts;
    }

    getAttributes(line) {
        return [...(line.attribute_value_ids || [])];
    }

    async cancelOrder() {
        this.dialog.add(CancelPopup, {
            title: _t("Cancel order"),
            confirm: async () => {
                this.selfOrder.cancelBackendOrder();
            },
        });
    }

    getLineChangeQty(line) {
        const currentQty = line.qty;
        const lastChange = this.selfOrder.currentOrder.uiState.lineChanges[line.uuid];
        return !lastChange ? currentQty : currentQty - lastChange.qty;
    }

    async pay() {
        const presets = this.selfOrder.models["pos.preset"].getAll();
        const config = this.selfOrder.config;
        const type = config.self_ordering_mode;
        const orderingMode =
            config.use_presets && presets.length > 1
                ? this.selfOrder.currentOrder.preset_id?.service_at
                : config.self_ordering_service_mode;
        const useTiming =
            config.use_presets &&
            presets.length > 0 &&
            this.selfOrder.currentOrder.preset_id?.use_timing;

        if (this.selfOrder.rpcLoading || !this.selfOrder.verifyCart()) {
            return;
        }

        if (!this.selfOrder.currentOrder.presetRequirementsFilled && orderingMode !== "table") {
            let result = null;

            // Show timing selection popup only if preset uses timing
            if (useTiming) {
                result = await makeAwaitable(this.dialog, PillsSelectionPopup, {
                    options: this.presetTimingOptions,
                    title: _t("Select a hour"),
                    subtitle: _t("Please choose a time slot for your order."),
                    selectionType: "time",
                });
                if (!result) {
                    return;
                }
            }

            // Always show preset info popup when requirements aren't filled
            const infos = await makeAwaitable(this.dialog, PresetInfoPopup, {});
            if (!infos) {
                return;
            }

            const email = this.selfOrder.currentOrder.partner_id?.email || infos.email;
            this.selfOrder.currentOrder.email = email;

            // Set preset time only if timing was selected
            if (result) {
                this.selfOrder.currentOrder.preset_time = DateTime.fromSQL(result);
            }
        }

        if (
            type === "mobile" &&
            orderingMode === "table" &&
            !this.selfOrder.currentTable &&
            this.selfOrder.config.module_pos_restaurant
        ) {
            const table = await makeAwaitable(this.dialog, PillsSelectionPopup, {
                options: this.tableOptions,
                title: _t("Select a table"),
                subtitle: _t("Please choose a table for your order."),
                selectionType: "table",
            });
            if (!table) {
                return;
            }

            const tableRecord = this.selfOrder.models["restaurant.table"].get(table);
            this.selectTableDependingOnMode(tableRecord);
            this.router.addTableIdentifier(tableRecord);
        } else if (this.selfOrder.currentTable) {
            this.selectTableDependingOnMode(this.selfOrder.currentTable);
        }
        const noteText = this.state.orderNoteValue.trim();
        if (noteText) {
            this.selfOrder.currentOrder.general_customer_note = noteText;
        }
        this.selfOrder.rpcLoading = true;
        await this.selfOrder.confirmOrder();
        this.selfOrder.rpcLoading = false;
    }

    get presetTimingOptions() {
        const availabilities = this.selfOrder.currentOrder.preset_id.availabilities;
        const options = {
            categories: {},
        };

        for (const [date, slots] of Object.entries(availabilities)) {
            options.categories[date] = {
                id: date,
                name: DateTime.fromISO(date).toLocaleString(DateTime.DATE_SHORT),
                subCategories: {},
            };

            for (const slot of Object.values(slots)) {
                if (!options.categories[date].subCategories[slot.periode]) {
                    let periodeName = _t("Full Day");

                    switch (slot.periode) {
                        case "morning":
                            periodeName = _t("Morning");
                            break;
                        case "afternoon":
                            periodeName = _t("Afternoon");
                            break;
                        case "evening":
                            periodeName = _t("Evening");
                            break;
                    }

                    options.categories[date].subCategories[slot.periode] = {
                        id: slot.periode,
                        name: periodeName,
                        options: [],
                    };
                }

                options.categories[date].subCategories[slot.periode].options.push({
                    id: slot.datetime.toFormat("yyyy-MM-dd HH:mm:ss"),
                    name: this.selfOrder.getTime(slot.datetime),
                });
            }
        }

        // Remove empty categories
        for (const dateId of Object.keys(options.categories)) {
            if (
                Object.keys(options.categories[dateId].subCategories).length === 0 ||
                Object.values(options.categories[dateId].subCategories).every(
                    (subCateg) => subCateg.options.length === 0
                )
            ) {
                delete options.categories[dateId];
            }
        }

        return options;
    }

    get tableOptions() {
        const options = {
            categories: {},
        };

        for (const table of this.selfOrder.models["restaurant.table"].getAll()) {
            if (!options.categories[table.floor_id.id]) {
                options.categories[table.floor_id.id] = {
                    id: table.floor_id.id,
                    name: table.floor_id.name,
                    subCategories: {
                        table: {
                            id: table.floor_id.id + "odd",
                            name: false,
                            options: [],
                        },
                    },
                };
            }

            options.categories[table.floor_id.id].subCategories.table.options.push({
                id: table.id,
                name: table.table_number,
            });
        }

        return options;
    }

    selectTableDependingOnMode(table) {
        if (this.selfOrder.config.self_ordering_pay_after === "each") {
            this.selfOrder.currentOrder.floating_order_name = _t(
                "Self-Order T %s",
                table.table_number
            );
        } else {
            this.selfOrder.currentOrder.self_ordering_table_id = table;
        }
    }

    selectTable(table) {
        if (table) {
            this.selectTableDependingOnMode(table);
            this.router.addTableIdentifier(table);
            this.pay();
        }

        this.state.selectTable = false;
    }

    getPrice(line) {
        const childLines = line.combo_line_ids;
        if (childLines.length === 0) {
            const qty = this.getLineChangeQty(line) || line.qty;
            return line.getDisplayPriceWithQty(qty);
        } else {
            let price = 0;
            for (const child of childLines) {
                const qty = this.getLineChangeQty(child) || child.qty;
                price += child.getDisplayPriceWithQty(qty);
            }
            return price;
        }
    }

    canChangeQuantity(line) {
        const order = this.selfOrder.currentOrder;
        const lastChange = order.uiState.lineChanges[line.uuid];
        if (!lastChange) {
            return true;
        }
        return lastChange.qty < line.qty;
    }

    canDeleteLine(line) {
        const lastChange = this.selfOrder.currentOrder.uiState.lineChanges[line.uuid];
        return !lastChange ? true : lastChange.qty !== line.qty;
    }

    removeLine(line, event) {
        if (!this.canDeleteLine(line)) {
            return;
        }
        const lastChange = this.selfOrder.currentOrder.uiState.lineChanges[line.uuid];
        if (lastChange) {
            line.qty = lastChange.qty;
            return;
        }

        const doRemoveLine = () => {
            this.selfOrder.removeLine(line);
            if (this.lines.length === 0) {
                this.router.navigate("product_list");
            }
        };
        const card = event?.target.closest(".product-cart-item");
        if (!card) {
            doRemoveLine();
            return;
        }
        const onAnimationEnd = () => {
            card.removeEventListener("animationend", onAnimationEnd);
            doRemoveLine();
        };
        card.addEventListener("animationend", onAnimationEnd);
        card.classList.add("delete-fade-out");
    }

    changeQuantity(line, increase) {
        if (!increase && !this.canChangeQuantity(line)) {
            return;
        }

        // Update combo first
        for (const cline of line.combo_line_ids) {
            this.changeQuantity(cline, increase);
        }

        increase ? line.qty++ : line.qty--;

        if (line.qty <= 0) {
            this.removeLine(line);
        }
    }

    getCustomValue(line, attr) {
        return (
            attr.is_custom &&
            line.custom_attribute_value_ids.find(
                (c) => c.custom_product_template_attribute_value_id === attr
            )?.custom_value
        );
    }
    get displayTaxes() {
        return !this.selfOrder.isTaxesIncludedInPrice();
    }

    formatProductName(product) {
        return formatProductName(product);
    }

    /*
    //TODO editable line
        clickOnLine(line) {
        const order = this.selfOrder.currentOrder;
        this.selfOrder.editedLine = line;

        if (order.state === "draft" && !order.lastChangesSent[line.uuid]) {
            this.selfOrder.selectedOrderUuid = order.uuid;

            if (line.combo_line_ids.length > 0) {
                this.router.navigate("combo_selection", { id: line.product_id });
            } else {
                this.router.navigate("product", { id: line.product_id });
            }
        } else {
            this.selfOrder.notification.add(_t("You cannot edit a posted orderline !"), {
                type: "danger",
            });
        }
    }
*/
}
