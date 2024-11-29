import { Component, onWillUnmount, useState, useSubEnv } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { AttributeSelection } from "@pos_self_order/app/components/attribute_selection/attribute_selection";
import { useService } from "@web/core/utils/hooks";

export class ProductPage extends Component {
    static template = "pos_self_order.ProductPage";
    static props = ["productTemplate", "back?", "onValidate?"];
    static components = { AttributeSelection };

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        useSubEnv({ selectedValues: {}, customValues: {}, editable: this.editableProductLine });

        if (!this.props.productTemplate) {
            this.router.navigate("product_list");
            return;
        }

        this.selfOrder.lastEditedProductId = this.props.productTemplate.id;
        this.state = useState({
            qty: 1,
            customer_note: "",
            product: this.props.productTemplate,
            selectedValues: this.env.selectedValues,
        });

        this.initState();

        onWillUnmount(() => {
            this.selfOrder.editedLine = null;
        });
    }

    get productTemplate() {
        return this.props.productTemplate;
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

    changeQuantity(increase) {
        const currentQty = this.state.qty;

        if (!increase && currentQty === 1) {
            return;
        }

        return increase ? this.state.qty++ : this.state.qty--;
    }

    get showQtyButtons() {
        return this.props.productTemplate.self_order_available;
    }
    addToCart() {
        this.selfOrder.addToCart(
            this.props.productTemplate,
            this.state.qty,
            this.state.customer_note,
            this.env.selectedValues,
            this.env.customValues
        );
        this.router.back();
    }

    isEveryValueSelected() {
        return Object.values(this.state.selectedValues).find((value) => !value) == false;
    }

    isArchivedCombination() {
        const variantAttributeValueIds = Object.values(this.state.selectedValues)
            .filter((attr) => typeof attr !== "object")
            .map((attr) => Number(attr));
        return this.props.productTemplate._isArchivedCombination(variantAttributeValueIds);
    }
}
