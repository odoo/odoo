import { Component } from "@odoo/owl";
import { useDropdownCloser } from "@web/core/dropdown/dropdown_hooks";

const ClosingMode = {
    None: "none",
    ClosestParent: "closest",
    AllParents: "all",
};

export class DropdownItem extends Component {
    static template = "web.DropdownItem";
    static props = {
        tag: {
            type: String,
            optional: true,
        },
        class: {
            type: [String, Object],
            optional: true,
        },
        onSelected: {
            type: Function,
            optional: true,
        },
        closingMode: {
            type: ClosingMode,
            optional: true,
        },
        attrs: {
            type: Object,
            optional: true,
        },
        slots: { Object, optional: true },
    };
    static defaultProps = {
        closingMode: ClosingMode.AllParents,
        attrs: {},
    };

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
