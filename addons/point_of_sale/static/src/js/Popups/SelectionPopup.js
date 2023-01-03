/** @odoo-module */

import AbstractAwaitablePopup from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import Registries from "@point_of_sale/js/Registries";
import { _lt } from "@web/core/l10n/translation";

const { useState } = owl;

// formerly SelectionPopupWidget
class SelectionPopup extends AbstractAwaitablePopup {
    /**
     * Value of the `item` key of the selected element in the Selection
     * Array is the payload of this popup.
     *
     * @param {Object} props
     * @param {String} [props.confirmText='Confirm']
     * @param {String} [props.cancelText='Cancel']
     * @param {String} [props.title='Select']
     * @param {String} [props.body='']
     * @param {Array<Selection>} [props.list=[]]
     *      Selection {
     *          id: integer,
     *          label: string,
     *          isSelected: boolean,
     *          item: any,
     *      }
     */
    setup() {
        super.setup();
        this.state = useState({ selectedId: this.props.list.find((item) => item.isSelected) });
    }
    selectItem(itemId) {
        this.state.selectedId = itemId;
        this.confirm();
    }
    /**
     * We send as payload of the response the selected item.
     *
     * @override
     */
    getPayload() {
        const selected = this.props.list.find((item) => this.state.selectedId === item.id);
        return selected && selected.item;
    }
}
SelectionPopup.template = "SelectionPopup";
SelectionPopup.defaultProps = {
    cancelText: _lt("Cancel"),
    title: _lt("Select"),
    body: "",
    list: [],
    confirmKey: false,
};

Registries.Component.add(SelectionPopup);

export default SelectionPopup;
