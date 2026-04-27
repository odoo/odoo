import { Component } from "@odoo/owl";
import { registries } from "@spreadsheet/o_spreadsheet/o_spreadsheet";
import { SpreadsheetShareButton } from "@spreadsheet/components/share_button/share_button";

const { topbarComponentRegistry } = registries;

export class TopbarShareButton extends Component {
    static template = "spreadsheet_edition.TopbarShareButton";
    static components = {
        SpreadsheetShareButton,
    };
    static props = {};

    get buttonProps() {
        return {
            onSpreadsheetShared: this.env.onSpreadsheetShared.bind(this),
            model: this.env.model,
        };
    }
}

topbarComponentRegistry.add("share_button", {
    component: TopbarShareButton,
    isVisible: (env) => env.onSpreadsheetShared,
    sequence: 20,
});
