import { registry } from "@web/core/registry";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { _t } from "@web/core/l10n/translation";
import { BinaryField, binaryField } from "@web/views/fields/binary/binary_field";
import { useService } from "@web/core/utils/hooks";

export class SpreadsheetBinaryField extends BinaryField {
    static template = "spreadsheet.SpreadsheetBinaryField";

    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    async onFileDownload() {
        this.dialog.add(WarningDialog, {
            title: _t("Warning"),
            message: _t(
                "Dashboard JSON file cannot be downloaded here. Please open the dashboard, activate debug mode and go the File → Download as JSON. "
            ),
        });
    }
}

export const spreadsheetBinaryField = {
    ...binaryField,
    component: SpreadsheetBinaryField,
};

registry.category("fields").add("spreadsheetBinary", spreadsheetBinaryField);
