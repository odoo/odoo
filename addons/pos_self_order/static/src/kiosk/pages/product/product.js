/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useselfOrder } from "@pos_self_order/kiosk/self_order_kiosk_service";
import { AttributeSelection } from "@pos_self_order/kiosk/components/attribute_selection/attribute_selection";
import { KioskTemplate } from "@pos_self_order/kiosk/template/kiosk_template";
import { Line } from "@pos_self_order/common/models/line";
import { useService } from "@web/core/utils/hooks";
import { flattenSelectedAttribute } from "@pos_self_order/common/utils";

export class Product extends Component {
    static template = "pos_self_order.Product";
    static props = ["product", "back?", "onValidate?"];
    static components = { AttributeSelection, KioskTemplate };

    setup() {
        this.selfOrder = useselfOrder();
        this.router = useService("router");

        if (!this.props.product) {
            this.router.navigate("productList");
            return;
        }

        this.selfOrder.lastEditedProductId = this.props.product.id;
        this.state = useState({
            qty: 1,
            customer_note: "",
            selectedVariants: {},
            showQtyButtons: false,
            product: this.props.product,
        });
    }

    get product() {
        return this.state.product;
    }

    back() {
        this.router.navigate("product_list");
    }

    changeQuantity(increase) {
        const currentQty = this.state.qty;

        if (!increase && currentQty === 1) {
            return;
        }

        return increase ? this.state.qty++ : this.state.qty--;
    }

    async addToCart() {
        const lines = this.selfOrder.currentOrder.lines;

        lines.push(
            new Line({
                id: null,
                uuid: null,
                qty: this.state.qty,
                product_id: this.product.id,
                customer_note: this.state.customer_note,
                price_subtotal_incl: this.product.price_info.display_price,
                selected_attributes: flattenSelectedAttribute(this.state.selectedVariants),
            })
        );

        await this.selfOrder.getPricesFromServer();
        this.router.back();
    }

    get attributeSelection() {
        if (this.product.attributes.length === 0) {
            this.state.showQtyButtons = true;
        }

        return this.product.attributes.length > 0;
    }
}
