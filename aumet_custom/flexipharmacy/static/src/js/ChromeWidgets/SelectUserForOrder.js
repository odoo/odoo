odoo.define('flexipharmacy.SelectUserForOrder', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    class SelectUserForOrder extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('open-user-select-popup', this.OpenUserSelectPopup);
        }
        async OpenUserSelectPopup() {
            const userSelectionList = this.env.pos.users.map(user => ({
                id: user.id,
                label: user.name,
                isSelected: user.id 
                    ? user.id === this.env.pos.get_order().get_sales_person_id()
                    : false,
                item: user,
            }));
            const { confirmed, payload: selectedUser } = await this.showPopup(
                'SelectionPopup',
                {
                    title: this.env._t('Select the User'),
                    list: userSelectionList,
                }
            );
            if (confirmed) {
                this.env.pos.get_order().set_sales_person_id(selectedUser.id);
            }
        }
        get isActive(){
            return this.env.pos.get_order().get_sales_person_id() ? true : false;
        }
    }
    SelectUserForOrder.template = 'SelectUserForOrder';

    Registries.Component.add(SelectUserForOrder);

    return SelectUserForOrder;
});
