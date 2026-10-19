import {
    SelectCreateDialog,
    selectCreateDialogProps,
} from "@web/views/view_dialogs/select_create_dialog";
import { useProps, t } from "@odoo/owl";

export class CustomSelectCreateDialog extends SelectCreateDialog {
    props = useProps({
        ...selectCreateDialogProps,
        listViewId: t.or([t.number(), t.literal(false)]).optional(),
    });

    get viewProps() {
        const viewProps = super.viewProps;
        if (this.props.listViewId) {
            viewProps.viewId = this.props.listViewId;
            viewProps.type = "list";
        }
        return viewProps;
    }
}

import { registry } from "@web/core/registry";
registry.category("dialogs").add("custom_select_create", CustomSelectCreateDialog);
