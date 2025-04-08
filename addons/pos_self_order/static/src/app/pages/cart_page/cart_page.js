import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { PopupTable } from "@pos_self_order/app/components/popup_table/popup_table";
import { _t } from "@web/core/l10n/translation";
import { OrderWidget } from "@pos_self_order/app/components/order_widget/order_widget";
import { PresetInfoPopup } from "@pos_self_order/app/components/preset_info_popup/preset_info_popup";
import { ProductCard } from "@pos_self_order/app/components/product_card/product_card";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";

export class CartPage extends Component {
    static template = "pos_self_order.CartPage";
    static components = { PopupTable, OrderWidget, PresetInfoPopup, ProductCard };
    static props = {};

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.state = useState({
            selectTable: false,
            fillInformations: false,
            cancelConfirmation: false,
        });
        this.renderer = useService("renderer");
        this.sendReceipt = useTrackedAsync(this._sendReceiptToCustomer.bind(this));
    }

    get lines() {
        const lines = this.selfOrder.currentOrder.lines;
        return lines ? lines : [];
    }

    get linesToDisplay() {
        const selfOrder = this.selfOrder;
        const order = selfOrder.currentOrder;

        if (
            selfOrder.config.self_ordering_pay_after === "meal" &&
            Object.keys(order.changes).length > 0
        ) {
            return order.unsentLines;
        } else {
            return this.lines;
        }
    }

    get optionalProducts() {
        const optionalProducts =
            this.selfOrder.currentOrder.lines.flatMap(
                (line) => line.product_id.product_tmpl_id.pos_optional_product_ids
            ) || [];
        return optionalProducts;
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
        } else {
            this.selfOrder.currentOrder.table_id = this.selfOrder.currentTable;
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

    generateTicketImage = async () =>
        await this.renderer.toJpeg(
            OrderReceipt,
            {
                order: this.selfOrder.currentOrder,
            },
            { addClass: "pos-receipt-print p-3" }
        );
    async _sendReceiptToCustomer({ action, destination, mail_template_id }) {
        const order = this.selfOrder.currentOrder;
        const fullTicketImage = await this.generateTicketImage();
        const basicTicketImage = await this.generateTicketImage(true);

        await this.selfOrder.data.call("pos.order", action, [
            [order.id],
            destination,
            mail_template_id,
            fullTicketImage,
            this.selfOrder.config.basic_receipt ? basicTicketImage : null,
        ]);
    }

    selectTable(table) {
        if (table) {
            this.selfOrder.currentOrder.table_id = table;
            this.selfOrder.currentTable = table;
            this.router.addTableIdentifier(table);
            this.pay();
        }

        this.state.selectTable = false;
    }

    getPrice(line) {
        const childLines = line.combo_line_ids;
        if (childLines.length == 0) {
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

    async removeLine(line) {
        const lastChange = this.selfOrder.currentOrder.uiState.lineChanges[line.uuid];

        if (!this.canDeleteLine(line)) {
            return;
        }

        if (lastChange) {
            line.qty = lastChange.qty;
        } else {
            this.selfOrder.removeLine(line);
        }
    }

    async _changeQuantity(line, increase) {
        if (!increase && !this.canChangeQuantity(line)) {
            return;
        }

        if (!increase && line.qty === 1) {
            this.removeLine(line.uuid);
            return;
        }
        increase ? line.qty++ : line.qty--;
        for (const cline of this.selfOrder.currentOrder.lines) {
            if (cline.combo_parent_id?.uuid === line.uuid) {
                this._changeQuantity(cline, increase);
            }
        }
    }

    async changeQuantity(line, increase) {
        await this._changeQuantity(line, increase);
    }

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
}
