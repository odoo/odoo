import { _t } from "@web/core/l10n/translation";
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class SelectionPopup extends Component {
    static template = "point_of_sale.SelectionPopup";
    static components = { Dialog };
    static props = {
        title: { type: String, optional: true },
        list: { type: Array, optional: true },
        getPayload: Function,
        close: Function,
        size: { type: String, optional: true },
    };
    static defaultProps = {
        title: _t("Select"),
        list: [],
    };

    /**
     * Value of the `item` key of the selected element in the Selection
     * Array is the payload of this popup.
     *
     * @param {Object} props
     * @param {String} [props.title='Select']
     * @param {Array<Selection>} [props.list=[]]
     *      Selection {
     *          id: integer,
     *          label: string,
     *          isSelected: boolean,
     *          item: any,
     *      }
     */
    setup() {
        this.state = useState({ selectedId: this.props.list.find((item) => item.isSelected) });
    }
    selectItem(itemId) {
        this.state.selectedId = itemId;
        this.confirm();
    }
    computePayload() {
        const selected = this.props.list.find((item) => this.state.selectedId === item.id);
        return selected && selected.item;
    }
    confirm() {
        this.props.getPayload(this.computePayload());
        this.props.close();
    }
    get size() {
        return this.props.size || "lg";
    }
}
