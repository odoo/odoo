odoo.define('aumet_pos_flexipharmacy_fix.EditListPopup', function (require) {
    'use strict';

    const EditListPopup = require('point_of_sale.EditListPopup');
    const Registries = require('point_of_sale.Registries');


    const AsplEditListPopupInh = (EditListPopup) =>
        class extends EditListPopup {
            constructor() {
                super(...arguments);
                try {
                    const serial = this.props.serials.filter(item => item.product_qty > 0)[0];
                    this.state.array = [{text: serial.name, _id: 0}]
                    const uom = this.props.uom_list.filter(item => serial.product_qty / item.factor_inv >= 1)[0];
                    this.state.selected_uom = [uom.id, uom.name]
                } catch (e) {
                    return
                }

            }

            onLotChange() {
                const serial = document.getElementById('lot_serial').value;
                this.state.array = [{text: serial, _id: 0}]
                const serial_object = this.props.serials.filter(item => item.name === serial)[0];
                this.props.qty = serial_object.product_qty
                this.props.expiration_date = serial_object.expiration_date

            }

            onUOMSelect(uom) {
                this.state.selected_uom = [uom.id, uom.name]
            }

            getPayload() {
                return {
                    newArray: this.state.array
                        .filter((item) => item.text.trim() !== '')
                        .map((item) => Object.assign({}, item)),
                    selected_uom: this.state.selected_uom
                };
            }
        }

    Registries.Component.extend(EditListPopup, AsplEditListPopupInh);

    return EditListPopup;
});
