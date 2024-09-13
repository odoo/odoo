import { patch } from "@web/core/utils/patch";
import { useAsyncLockedMethod } from "@point_of_sale/app/utils/hooks";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

patch(SelectCreateDialog, {
    props: {
        ...SelectCreateDialog.props,
        listViewId: { type: [Number, { value: false }], optional: true },
        kanbanViewId: { type: [Number, { value: false }], optional: true },
        size: { type: String, optional: true },
        closeIfSelectCancel: { type: Boolean, optional: true }, // If this prop is set to false, the onSelect props should return a success status.
    },
    defaultProps: {
        ...SelectCreateDialog.defaultProps,
        listViewId: false,
        kanbanViewId: false,
        size: "lg",
        closeIfSelectCancel: true,
    },
});

patch(SelectCreateDialog.prototype, {
    setup() {
        super.setup();
        this.trackedSelect = useAsyncLockedMethod(this.props.onSelected);
    },
    get viewProps() {
        const props = super.viewProps;
        if (this.props.kanbanViewId && props.type === "kanban") {
            props.viewId = this.props.kanbanViewId;
        } else if (this.props.listViewId) {
            props.viewId = this.props.listViewId;
            props.type = "list";
        }
        return props;
    },
    async select(resIds) {
        if (this.props.onSelected) {
            if (this.props.closeIfSelectCancel) {
                await super.select(resIds);
            } else {
                const res = await this.trackedSelect(resIds);
                if (res) {
                    this.props.close();
                }
            }
        }
    },
});
