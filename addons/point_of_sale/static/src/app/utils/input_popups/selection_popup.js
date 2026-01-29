/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _t } from "@web/core/l10n/translation";
import { useState } from "@odoo/owl";

export class SelectionPopup extends AbstractAwaitablePopup {
    static template = "point_of_sale.SelectionPopup";
    static defaultProps = {
        cancelText: _t("Cancel"),
        title: _t("Select"),
        body: "",
        list: [],
        confirmKey: false,
    };

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
