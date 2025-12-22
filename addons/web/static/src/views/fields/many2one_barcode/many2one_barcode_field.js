import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { many2OneField, Many2OneField } from "../many2one/many2one_field";

export class Many2OneBarcodeField extends Many2OneField {
    static defaultProps = {
        ...super.defaultProps,
        canScanBarcode: true,
    };
}

export const many2OneBarcodeField = {
    ...many2OneField,
    component: Many2OneBarcodeField,
    displayName: _t("Many2OneBarcode"),
    extractProps() {
        const props = many2OneField.extractProps(...arguments);
        props.canScanBarcode = true;
        return props;
    },
};

registry.category("fields").add("many2one_barcode", many2OneBarcodeField);
