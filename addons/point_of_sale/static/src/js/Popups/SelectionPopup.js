odoo.define('point_of_sale.SelectionPopup', function (require) {
    'use strict';

    const { useState } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');

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
        constructor() {
            super(...arguments);
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
    SelectionPopup.template = 'SelectionPopup';
    SelectionPopup.defaultProps = {
        confirmText: _lt('Confirm'),
        cancelText: _lt('Cancel'),
        title: _lt('Select'),
        body: '',
        list: [],
    };

    Registries.Component.add(SelectionPopup);

    return SelectionPopup;
});
