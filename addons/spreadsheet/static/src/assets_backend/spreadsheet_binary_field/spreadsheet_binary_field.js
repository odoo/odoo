import { registry } from "@web/core/registry";
import { BinaryField, binaryField } from "@web/views/fields/binary/binary_field";

export class SpreadsheetBinaryField extends BinaryField {
    static template = "spreadsheet.SpreadsheetBinaryField";

    setup() {
        super.setup();
    }

    async onFileDownload() {}
}

export const spreadsheetBinaryField = {
    ...binaryField,
    component: SpreadsheetBinaryField,
};

registry.category("fields").add("binary_spreadsheet", spreadsheetBinaryField);
