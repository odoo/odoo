import { Spreadsheet } from "@odoo/o-spreadsheet";
import { patch } from "@web/core/utils/patch";
import { useSpreadsheetCommandPalette } from "./command_provider";

patch(Spreadsheet.prototype, {
    setup() {
        super.setup();
        if (this.env.isDashboard()) {
            return;
        }
        useSpreadsheetCommandPalette();
    },
});
