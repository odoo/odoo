import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class PermissionPromptDialog extends Component {
    static components = { Dialog };
    static template = "web.PermissionPromptDialog";
    static props = [
        "title?",
        "contentClass?",
        "close?",
        "slots?",
        "size?",
        "illustrationPosition?",
    ];

    setup() {
        this.ui = useService("ui");
    }
}
