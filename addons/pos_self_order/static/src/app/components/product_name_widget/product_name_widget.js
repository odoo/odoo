import { Component, props, t } from "@odoo/owl";
import { ProductInfoPopup } from "../product_info_popup/product_info_popup";
import { useService } from "@web/core/utils/hooks";
import { formatProductName } from "../../utils";
import { ProductTemplate } from "@point_of_sale/app/models/product_template";
import { ProductProduct } from "@point_of_sale/app/models/product_product";

export class ProductNameWidget extends Component {
    static template = "pos_self_order.ProductNameWidget";
    props = props({
        product: t.or([t.instanceOf(ProductProduct), t.instanceOf(ProductTemplate)]),
    });
    setup() {
        this.dialog = useService("dialog");
    }

    displayProductInfo() {
        this.dialog.add(ProductInfoPopup, {
            productTemplate: this.props.product,
        });
    }

    formatProductName(product) {
        return formatProductName(product);
    }
}
