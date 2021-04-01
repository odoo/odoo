/** @odoo-module **/

const { Component, QWeb } = owl;

export const ParentClosingMode = {
  None: "none",
  ClosestParent: "closest",
  AllParents: "all",
};

export class DropdownItem extends Component {
  /**
   * Handlers
   */
  onClick(ev) {
    const payload = {
      payload: this.props.payload,
      dropdownClosingRequest: {
        isFresh: true,
        mode: this.props.parentClosingMode,
      },
    };
    this.trigger("dropdown-item-selected", payload);
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
  title: {
    type: String,
    optional: true,
  },
};
DropdownItem.defaultProps = {
  parentClosingMode: ParentClosingMode.AllParents,
};

QWeb.registerComponent("DropdownItem", DropdownItem);
