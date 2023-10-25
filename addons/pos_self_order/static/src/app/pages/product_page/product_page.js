/** @odoo-module */

import { Component, onWillUnmount, useState, useSubEnv } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { AttributeSelection } from "@pos_self_order/app/components/attribute_selection/attribute_selection";
import { Line } from "@pos_self_order/app/models/line";
import { useService } from "@web/core/utils/hooks";
import { attributeFlatter } from "@pos_self_order/app/utils";
import { constructFullProductName } from "@point_of_sale/utils";

export class ProductPage extends Component {
    static template = "pos_self_order.ProductPage";
    static props = ["product", "back?", "onValidate?"];
    static components = { AttributeSelection };

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        useSubEnv({ selectedValues: {}, customValues: {}, editable: this.editableProductLine });

        if (!this.props.product) {
            this.router.navigate("productList");
            return;
        }

        this.selfOrder.lastEditedProductId = this.props.product.id;
        this.state = useState({
            qty: 1,
            customer_note: "",
            product: this.props.product,
            selectedValues: this.env.selectedValues,
        });

        this.initState();

        onWillUnmount(() => {
            this.selfOrder.editedLine = null;
        });
    }

    get product() {
        return this.props.product;
    }

    get attributes() {
        return this.product.attributes;
    }

    get editableProductLine() {
        const order = this.selfOrder.currentOrder;
        return !(
            this.selfOrder.editedLine &&
            this.selfOrder.editedLine.uuid &&
            order.lastChangesSent[this.selfOrder.editedLine.uuid]
        );
    }

    initState() {
        const editedLine = this.selfOrder.editedLine;

        if (editedLine) {
            this.state.customer_note = editedLine.customer_note;
            this.state.qty = editedLine.qty;
        }

        return 0;
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

    orderlineCanBeMerged() {
        if (this.props.product.pos_combo_ids.length) {
            return false;
        }
        const editedLine = this.selfOrder.editedLine;

        if (editedLine) {
            return editedLine;
        }

        const line = this.selfOrder.currentOrder.lines.find(
            (l) =>
                JSON.stringify(l.attribute_value_ids.sort()) ===
                    JSON.stringify(attributeFlatter(this.env.selectedValues).sort()) &&
                l.customer_note === this.state.customer_note &&
                l.product_id === this.product.id
        );

        return line || false;
    }

    async addToCart() {
        const lines = this.selfOrder.currentOrder.lines;
        const lineToMerge = this.orderlineCanBeMerged();

        if (lineToMerge) {
            lineToMerge.attribute_value_ids = attributeFlatter(this.env.selectedValues);
            lineToMerge.customer_note = this.state.customer_note;
            lineToMerge.full_product_name = this.product.name;

            if (this.selfOrder.editedLine) {
                lineToMerge.qty = this.state.qty;
            } else {
                lineToMerge.qty += this.state.qty;
            }
        } else {
            const mainLine = new Line({
                id: lineToMerge ? lineToMerge.id : null,
                uuid: lineToMerge ? lineToMerge.uuid : null,
                qty: this.state.qty,
                product_id: this.product.id,
                customer_note: this.state.customer_note,
                custom_attribute_value_ids: Object.values(this.env.customValues),
                attribute_value_ids: attributeFlatter(this.env.selectedValues),
            });

            mainLine.full_product_name = constructFullProductName(
                mainLine,
                this.selfOrder.attributeValueById,
                this.product.name
            );

            lines.push(mainLine);
        }

        // If a command line does not have a quantity greater than 0, we consider it deleted
        await this.selfOrder.getPricesFromServer();
        this.selfOrder.currentOrder.lines = lines.filter((o) => o.qty > 0);

        if (this.selfOrder.currentOrder.lines.length === 0) {
            this.router.navigate("productList");
        } else {
            this.router.back();
        }
    }

    get showQtyButtons() {
        return this.props.product.self_order_available;
    }

    isEveryValueSelected() {
        return Object.values(this.state.selectedValues).find((value) => !value) == false;
    }
}
