/** @odoo-module **/

const { Component, QWeb } = owl;

/**
 * @enum {string}
 */
export const ParentClosingMode = {
    None: "none",
    ClosestParent: "closest",
    AllParents: "all",
};

/**
 * @typedef DropdownItemSelectedEventDetail
 * @property {*} payload
 * @property {Object} dropdownClosingRequest
 * @property {boolean} dropdownClosingRequest.isFresh
 * @property {ParentClosingMode} dropdownClosingRequest.mode
 *
 * @typedef {CustomEvent<DropdownItemSelectedEventDetail>} DropdownItemSelectedEvent
 */

/**
 * @extends Component
 */
export class DropdownItem extends Component {
    /**
     * Triggers a custom DropdownItemSelectedEvent
     * @param {MouseEvent} ev
     */
    onClick(ev) {
        if (this.props.href){
            ev.preventDefault();
        }

        /** @type DropdownItemSelectedEventDetail */
        const detail = {
            payload: this.props.payload,
            dropdownClosingRequest: {
                isFresh: true,
                mode: this.props.parentClosingMode,
            },
        };
        this.trigger("dropdown-item-selected", detail);
    }
}
DropdownItem.template = "web.DropdownItem";
DropdownItem.props = {
    payload: {
        type: Object,
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
    title: {
        type: String,
        optional: true,
    },
};
DropdownItem.defaultProps = {
    parentClosingMode: ParentClosingMode.AllParents,
};

QWeb.registerComponent("DropdownItem", DropdownItem);
