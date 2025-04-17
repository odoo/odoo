import { Component } from "@odoo/owl";

const EPSON_LABEL_FORMAT_SIZE = {
    width: 2.0,
    height: 1.0,
};

const DPI = 203;

export class PrintLabel extends Component {
    static template = "product.print_label";
    static props = {
        product: { type: Object },
    };

    get labelSize() {
        return {
            width: EPSON_LABEL_FORMAT_SIZE.width * DPI,
            height: EPSON_LABEL_FORMAT_SIZE.height * DPI,
        };
    }

    get barcodeSize() {
        return {
            width: this.labelSize.width * 0.9,
            height: this.labelSize.height * 0.3,
        };
    }
}
