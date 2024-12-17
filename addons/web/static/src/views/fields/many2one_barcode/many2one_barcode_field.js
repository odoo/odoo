import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2One, useMany2One } from "../many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    Many2OneField,
} from "../many2one/many2one_field";

export class Many2OneBarcodeField extends Component {
    static template = "web.Many2OneBarcodeField";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    setup() {
        this.m2o = useMany2One(() => this.props);
    }

    get m2oProps() {
        return this.m2o.computeProps();
    }
}

export const many2OneBarcodeField = {};

registry.category("fields").add("many2one_barcode", {
    ...buildM2OFieldDescription(Many2OneBarcodeField),
    displayName: _t("Many2OneBarcode"),
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            canScanBarcode: true,
        };
    },
});
