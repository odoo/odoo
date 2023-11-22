/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useBus, useService } from "@web/core/utils/hooks";
import { Component, xml } from "@odoo/owl";

export class BarcodeHandlerField extends Component {
    static template = xml``;
    static props = { ...standardFieldProps };
    setup() {
        const barcode = useService("barcode");
        useBus(barcode.bus, "barcode_scanned", this.onBarcodeScanned);
    }
    onBarcodeScanned(event) {
        const { barcode } = event.detail;
        this.props.record.update({ [this.props.name]: barcode });
    }
}

export const barcodeHandlerField = {
    component: BarcodeHandlerField,
};

registry.category("fields").add("barcode_handler", barcodeHandlerField);
