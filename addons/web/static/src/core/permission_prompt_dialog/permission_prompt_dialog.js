import { Component, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class PermissionPromptDialog extends Component {
    static components = { Dialog };
    static template = "web.PermissionPromptDialog";
    props = useProps({
        title: t.any().optional(),
        contentClass: t.any().optional(),
        close: t.any().optional(),
        slots: t.any().optional(),
        size: t.any().optional(),
        illustrationPosition: t.any().optional(),
    });

    setup() {
        this.ui = useService("ui");
    }
}
