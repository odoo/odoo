odoo.define('point_of_sale.SelectEmployeePopup', function (require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const SelectionPopup = require('point_of_sale.SelectionPopup');
    const useSelectEmployee = require('pos_hr.useSelectEmployee');
    const { useBarcodeReader } = require('point_of_sale.custom_hooks');
    const { Gui } = require('point_of_sale.Gui');

    const SelectEmployeePopup = (SelectionPopup) => {
        class SelectEmployeePopup extends SelectionPopup {
            constructor() {
                super(...arguments);
                const { askPin } = useSelectEmployee();
                this.askPin = askPin;
                this.env.pos.barcode_reader.enable();
                useBarcodeReader({ cashier: this._onCashierScan }, true);
            }
            async _onCashierScan(code) {
                const selectedItem = this.list.find(
                    (item) => item.barcode === Sha1.hash(code.code)
                );
                if (selectedItem) {
                    this.selectItem(selectedItem.id);
                } else {
                    await Gui.showPopup('ErrorPopup', {
                        title: this.env._t('Invalid badge'),
                        body: this.env._t('The scanned badge is not found in the employee list.'),
                    });
                    this.cancel();
                }
            }
        }
        SelectEmployeePopup.template = 'SelectEmployeePopup';
        return SelectEmployeePopup;
    };

    Registries.Component.addByExtending(SelectEmployeePopup, SelectionPopup);

    return SelectEmployeePopup;
});
