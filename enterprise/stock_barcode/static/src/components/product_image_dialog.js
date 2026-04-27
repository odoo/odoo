/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class ProductImageDialog extends Component {
    static components = { Dialog };
    static props = {
        record: Object,
        close: Function,
    };
    static template = "stock_barcode.ProductImageDialog";

    setup() {
        this.source = `/web/image/product.product/${this.props.record.id}/image_1024`;
        this.title = this.props.record.display_name;
    }
}
