import { EnterpriseNavBar } from "@web_enterprise/webclient/navbar/navbar";
import { SpreadsheetName } from "../../actions/control_panel/spreadsheet_name";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";

export class SpreadsheetNavbar extends EnterpriseNavBar {
    static template = "spreadsheet_edition.SpreadsheetNavbar";
    static components = { ...EnterpriseNavBar.components, SpreadsheetName };
    static props = {
        spreadsheetName: String,
        isReadonly: {
            type: Boolean,
            optional: true,
        },
        onSpreadsheetNameChanged: {
            type: Function,
            optional: true,
        },
        slots: {
            type: Object,
            optional: true,
        },
    };

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.breadcrumbs = useState(this.env.config.breadcrumbs);
    }

    get breadcrumbTitle() {
        if (this.breadcrumbs.length > 1) {
            return this.breadcrumbs.at(-2).name;
        }
        return "";
    }

    onBreadcrumbClicked() {
        if (this.breadcrumbs.length > 1) {
            this.actionService.restore(this.breadcrumbs.at(-2).id);
        }
    }
}
