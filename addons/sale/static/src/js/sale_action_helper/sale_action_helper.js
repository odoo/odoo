import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { SaleActionHelperDialog } from "./sale_action_helper_dialog"

export class SaleActionHelper extends Component {
    static template = "sale.SaleActionHelper";
    static props = {
        noContentHelp: String,
    }

    setup() {
        this.dialogService = useService("dialog");
    }

    openVideoPreview() {
        this.dialogService.add(SaleActionHelperDialog, {
            url: "https://www.youtube.com/embed/N4zw-2t6spk?autoplay=1",
        })
    }
};
