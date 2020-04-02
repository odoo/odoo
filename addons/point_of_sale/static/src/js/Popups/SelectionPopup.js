odoo.define('point_of_sale.SelectionPopup', function(require) {
    'use strict';

    const { useState } = owl.hooks;
    const { Chrome } = require('point_of_sale.chrome');
    const { addComponents } = require('point_of_sale.PosComponent');
    const { AbstractAwaitablePopup } = require('point_of_sale.AbstractAwaitablePopup');
    const Registry = require('point_of_sale.ComponentsRegistry');

    // formerly SelectionPopupWidget
    class SelectionPopup extends AbstractAwaitablePopup {
        static template = 'SelectionPopup';
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
            for (let item of this.list) {
                if (item.id === itemId) {
                    item.isSelected = true;
                } else {
                    item.isSelected = false;
                }
            }
            this.confirm();
        }
        /**
         * We send as payload of the response the selected item.
         *
         * @override
         */
        getPayload() {
            const selected = this.props.list.find(item => item.isSelected);
            return selected && selected.item;
        }
    }
    SelectionPopup.defaultProps = {
        confirmText: 'Confirm',
        cancelText: 'Cancel',
        title: 'Select',
        body: '',
        list: [],
    };

    addComponents(Chrome, [SelectionPopup]);

    Registry.add('SelectionPopup', SelectionPopup);

    return { SelectionPopup };
});
