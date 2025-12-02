import { Spreadsheet, components } from "@odoo/o-spreadsheet";
import { patch } from "@web/core/utils/patch";
import { useSpreadsheetCommandPalette } from "./command_provider";

const { Grid } = components;

patch(Spreadsheet.prototype, {
    setup() {
        super.setup();
        if (this.env.isDashboard()) {
            return;
        }
        useSpreadsheetCommandPalette();
    },
});

patch(Grid.prototype, {
    setup() {
        super.setup();
        // Remove the Ctrl+K hotkey (open a link) from the grid to avoid conflict
        // with the command palette.
        delete this.keyDownMapping["Ctrl+K"];
    },
});
