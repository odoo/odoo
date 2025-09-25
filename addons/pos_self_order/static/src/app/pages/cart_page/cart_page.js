import { Component, useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { PopupTable } from "@pos_self_order/app/components/popup_table/popup_table";
import { OrderWidget } from "@pos_self_order/app/components/order_widget/order_widget";
import { PresetInfoPopup } from "@pos_self_order/app/components/preset_info_popup/preset_info_popup";
import { useScrollShadow } from "../../utils/scroll_shadow_hook";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { CancelPopup } from "@pos_self_order/app/components/cancel_popup/cancel_popup";
import { _t } from "@web/core/l10n/translation";

export class CartPage extends Component {
    static template = "pos_self_order.CartPage";
    static components = { PopupTable, OrderWidget, PresetInfoPopup };
    static props = {};

    setup() {
        this.selfOrder = useSelfOrder();
        this.dialog = useService("dialog");
        this.router = useService("router");
        this.state = useState({
            selectTable: false,
            fillInformations: false,
            cancelConfirmation: false,
        });

        this.scrollShadow = useScrollShadow(useRef("scrollContainer"));
        this.renderer = useService("renderer");
        this.sendReceipt = useTrackedAsync(this._sendReceiptToCustomer.bind(this));
    }

    get showCancelButton() {
        return (
            this.selfOrder.config.self_ordering_mode === "mobile" &&
            this.selfOrder.config.self_ordering_pay_after === "each" &&
            this.selfOrder.currentOrder.isSynced
        );
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

        if (this.selfOrder.rpcLoading || !this.selfOrder.verifyCart()) {
            return;
        }

        if (!this.selfOrder.currentOrder.presetRequirementsFilled && orderingMode !== "table") {
            this.state.fillInformations = true;
            return;
        }

        if (
            type === "mobile" &&
            orderingMode === "table" &&
            !this.selfOrder.currentTable &&
            this.selfOrder.config.module_pos_restaurant
        ) {
            this.state.selectTable = true;
            return;
        } else if (this.selfOrder.currentTable) {
            this.selectTableDependingOnMode(this.selfOrder.currentTable);
        }

        this.selfOrder.rpcLoading = true;
        await this.selfOrder.confirmOrder();
        this.selfOrder.rpcLoading = false;
    }

    async proceedInfos(state) {
        this.state.fillInformations = false;
        if (state) {
            await this.pay();
            if (this.selfOrder.currentOrder.preset_id?.mail_template_id) {
                this.sendReceipt.call({
                    action: "action_send_self_order_receipt",
                    destination: state.email,
                    mail_template_id: this.selfOrder.currentOrder.preset_id.mail_template_id.id,
                });
            }
        }
    }

    generateTicketImage = async (basicReceipt = false) =>
        await this.renderer.toJpeg(
            OrderReceipt,
            {
                order: this.selfOrder.currentOrder,
                basic_receipt: basicReceipt,
            },
            { addClass: "pos-receipt-print p-3" }
        );

    async _sendReceiptToCustomer({ action, destination, mail_template_id }) {
        const order = this.selfOrder.currentOrder;
        const fullTicketImage = await this.generateTicketImage();
        const basicTicketImage = this.selfOrder.config.basic_receipt
            ? await this.generateTicketImage(true)
            : null;
        await this.selfOrder.data.call("pos.order", action, [
            [order.id],
            destination,
            mail_template_id,
            fullTicketImage,
            basicTicketImage,
        ]);
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
            this.selfOrder.currentTable = table;
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
