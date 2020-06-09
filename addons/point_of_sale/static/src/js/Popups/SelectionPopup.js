odoo.define('point_of_sale.SelectionPopup', function(require) {
    'use strict';

    const { useState } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

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
            this.list = useState([...this.props.list]);
        }
        selectItem(itemId) {
            this.selected = this.list.find(item => item.id === itemId);
            this.confirm();
        }
        /**
         * We send as payload of the response the selected item.
         *
         * @override
         */
        getPayload() {;
            return this.selected && this.selected.item;
        }
    }
    SelectionPopup.template = 'SelectionPopup';
    SelectionPopup.defaultProps = {
        confirmText: 'Confirm',
        cancelText: 'Cancel',
        title: 'Select',
        body: '',
        hideCancelButton: false,
        list: [],
    };

    Registries.Component.add(SelectionPopup);

    return SelectionPopup;
});
