import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { PopupTable } from "@pos_self_order/app/components/popup_table/popup_table";
import { OrderWidget } from "@pos_self_order/app/components/order_widget/order_widget";
import { PresetInfoPopup } from "@pos_self_order/app/components/preset_info_popup/preset_info_popup";
import { ProductCard } from "@pos_self_order/app/components/product_card/product_card";
import { payOrder } from "../cart_page/cart_page_utils";

export class KioskCartPage extends Component {
    static template = "pos_self_order.KioskCartPage";
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

        if (this.lines.length <= 0) {
            this.router.back();
        }
    }

    get lines() {
        return this.selfOrder.currentOrder.lines;
    }

    get optionalProducts() {
        const optionalProducts =
            this.selfOrder.currentOrder.lines.flatMap(
                (line) => line.product_id.product_tmpl_id.pos_optional_product_ids
            ) || [];
        return optionalProducts;
    }

    async pay() {
        await payOrder(this.selfOrder, this.state);
    }

    proceedInfos(state) {
        this.state.fillInformations = false;
        if (state) {
            this.pay();
        }
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
        if (childLines.length === 0) {
            return line.getDisplayPrice();
        } else {
            let price = 0;
            for (const child of childLines) {
                price += child.getDisplayPrice();
            }
            return price;
        }
    }

    removeLine(line) {
        this.selfOrder.removeLine(line);
        if (this.lines.length === 0) {
            this.router.back();
        }
    }

    changeQuantity(line, increase) {
        // Update combo first
        for (const cline of line.combo_line_ids) {
            this.changeQuantity(cline, increase);
        }

        if (line.combo_parent_id) {
            line.qty =
                (line.qty / line.combo_parent_id.qty) *
                (line.combo_parent_id.qty + (increase ? 1 : -1));
        } else {
            increase ? line.qty++ : line.qty--;
        }

        if (line.qty <= 0) {
            this.removeLine(line.uuid);
        }
    }

    get displayTaxes() {
        return !this.selfOrder.isTaxesIncludedInPrice();
    }
}
