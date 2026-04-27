import { Dialog } from "@web/core/dialog/dialog";
import { Component, useSubEnv } from "@odoo/owl";
import { components } from "@odoo/o-spreadsheet";

const { PivotHTMLRenderer } = components;

export class PivotMissingCellDialog extends Component {
    static template = "spreadsheet_edition.PivotMissingCellDialog";
    static components = { Dialog, PivotHTMLRenderer };
    static props = {
        close: Function,
        pivotId: String,
        model: Object,
        onCellClicked: Function,
    };

    setup() {
        useSubEnv({
            model: this.props.model,
        });
    }
}
