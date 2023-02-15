/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useBus, useService } from "@web/core/utils/hooks";

const { Component, xml } = owl;

export class BarcodeHandlerField extends Component {
    setup() {
        const barcode = useService("barcode");
        useBus(barcode.bus, "barcode_scanned", this.onBarcodeScanned);
    }
    onBarcodeScanned(event) {
        const { barcode } = event.detail;
        this.props.update(barcode);
    }
}

BarcodeHandlerField.template = xml``;
BarcodeHandlerField.props = { ...standardFieldProps };

registry.category("fields").add("barcode_handler", BarcodeHandlerField);
