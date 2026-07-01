import { Component, props, t } from "@odoo/owl";
import { useDropdownCloser } from "@web/core/dropdown/dropdown_hooks";

const ClosingMode = {
    None: "none",
    ClosestParent: "closest",
    AllParents: "all",
};

export const dropdownItemProps = {
    tag: t.string().optional(),
    class: t.or([t.string(), t.object()]).optional(),
    onSelected: t.function().optional(),
    closingMode: t.selection(Object.values(ClosingMode)).optional(ClosingMode.AllParents),
    attrs: t.object().optional({}),
};

export class DropdownItem extends Component {
    static template = "web.DropdownItem";
    props = props(dropdownItemProps);

    setup() {
        this.dropdownControl = useDropdownCloser();
    }

    onClick(ev) {
        if (this.props.attrs && this.props.attrs.href) {
            ev.preventDefault();
        }
        this.props.onSelected?.(ev);
        switch (this.props.closingMode) {
            case ClosingMode.ClosestParent:
                this.dropdownControl.close();
                break;
            case ClosingMode.AllParents:
                this.dropdownControl.closeAll();
                break;
        }
    }
}
