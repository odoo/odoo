import { Component } from "@odoo/owl";
import { registries } from "@spreadsheet/o_spreadsheet/o_spreadsheet";
import { SpreadsheetShareButton } from "@spreadsheet/components/share_button/share_button";

const { topbarComponentRegistry } = registries;

export class DocumentsTopbarFreezeAndShareButton extends Component {
    static template = "spreadsheet_edition.DocumentsTopbarFreezeAndShareButton";
    static components = {
        SpreadsheetShareButton,
    };
    static props = {};
}

topbarComponentRegistry.add("freeze_and_share_button", {
    component: DocumentsTopbarFreezeAndShareButton,
    isVisible: (env) => env.isFrozenSpreadsheet && !env.isFrozenSpreadsheet(),
    sequence: 27,
});
