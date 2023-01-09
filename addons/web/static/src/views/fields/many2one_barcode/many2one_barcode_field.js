/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2OneField } from "../many2one/many2one_field";

export class Many2OneBarcodeField extends Many2OneField {}

Many2OneBarcodeField.props = {
    ...Many2OneField.props,
};
Many2OneBarcodeField.defaultProps = {
    ...Many2OneField.defaultProps,
    canScanBarcode: true,
};

Many2OneBarcodeField.displayName = _lt("Many2OneBarcode");
Many2OneBarcodeField.template = "web.Many2OneField";
Many2OneBarcodeField.supportedTypes = ["many2one"];

Many2OneBarcodeField.extractProps = (args) => {
    return {
        ...Many2OneField.extractProps(args),
        canScanBarcode: true,
    };
};

registry.category("fields").add("many2one_barcode", Many2OneBarcodeField);
