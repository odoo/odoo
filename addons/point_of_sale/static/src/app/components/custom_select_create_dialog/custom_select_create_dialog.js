import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

export class CustomSelectCreateDialog extends SelectCreateDialog {
    static props = {
        ...SelectCreateDialog.props,
        listViewId: { type: [Number, { value: false }], optional: true },
    };

    get viewProps() {
        const props = super.viewProps;
        if (this.props.listViewId) {
            props.viewId = this.props.listViewId;
            props.type = "list";
        }
        return props;
    }
}

import { registry } from "@web/core/registry";
registry.category("dialogs").add("custom_select_create", CustomSelectCreateDialog);
