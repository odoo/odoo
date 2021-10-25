/** @odoo-module **/
import { DROPDOWN } from "./dropdown";

const { Component } = owl;

/**
 * @enum {string}
 */
const ParentClosingMode = {
    None: "none",
    ClosestParent: "closest",
    AllParents: "all",
};

export class DropdownItem extends Component {
    /**
     * Tells the parent dropdown that an item was selected and closes the
     * parent(s) dropdown according the the parentClosingMode prop.
     *
     * @param {MouseEvent} ev
     */
    onClick(ev) {
        if (this.props.href) {
            ev.preventDefault();
        }
        this.onSelected();
    }

    onSelected() {
        const { onSelected, parentClosingMode } = this.props;
        if (onSelected) {
            onSelected();
        }
        const dropdown = this.env[DROPDOWN];
        if (!dropdown) {
            return;
        }
        const { ClosestParent, AllParents } = ParentClosingMode;
        switch (parentClosingMode) {
            case ClosestParent:
                dropdown.close();
                break;
            case AllParents:
                dropdown.closeAllParents();
                break;
        }
    }
    get dataAttributes() {
        const { dataset } = this.props;
        if (this.props.dataset) {
            const attributes = Object.entries(dataset).map(([key, value]) => {
                return [`data-${key.replace(/[A-Z]/g, (char) => `-${char.toLowerCase()}`)}`, value];
            });
            return Object.fromEntries(attributes);
        }
        return {};
    }
}
DropdownItem.template = "web.DropdownItem";
DropdownItem.props = {
    onSelected: {
        type: Function,
        optional: true,
    },
    class: {
        type: [String, Object],
        optional: true,
    },
    parentClosingMode: {
        type: ParentClosingMode,
        optional: true,
    },
    hotkey: {
        type: String,
        optional: true,
    },
    href: {
        type: String,
        optional: true,
    },
    slots: {
        type: Object,
        optional: true,
    },
    title: {
        type: String,
        optional: true,
    },
    dataset: {
        type: Object,
        optional: true,
    },
};
DropdownItem.defaultProps = {
    parentClosingMode: ParentClosingMode.AllParents,
};
