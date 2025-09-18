// @ts-check

/** @module @web/fields/relational/many2one_barcode/many2one_barcode_field - Many2one field with barcode scanner support */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    Many2OneField,
} from "@web/fields/relational/many2one/many2one_field";

export class Many2OneBarcodeField extends Many2OneField {
    static template = "web.Many2OneBarcodeField";
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
