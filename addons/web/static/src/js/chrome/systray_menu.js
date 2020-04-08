odoo.define('web.SystrayMenu', function (require) {
"use strict";

const { ComponentAdapter } = require('web.OwlCompatibility');
const UserMenu = require('web.UserMenu');

class ItemAdapter extends ComponentAdapter {
    get widgetArgs() {
        return [this.env];
    }
}

class SystrayMenu extends owl.Component {
    constructor() {
        super(...arguments);
        this.Items = SystrayMenu.Items.slice();
        this.Items.sort((ItemA, ItemB) => {
            const cA = ItemA.prototype instanceof owl.Component ? ItemA : ItemA.prototype;
            const cB = ItemB.prototype instanceof owl.Component ? ItemB : ItemB.prototype;
            const seqA = cA.sequence !== undefined ? cA.sequence : 50;
            const seqB = cB.sequence !== undefined ? cB.sequence : 50;
            return seqB - seqA;
        });
    }
}
SystrayMenu.components = { ItemAdapter, UserMenu };
SystrayMenu.template = 'web.SystrayMenu';
SystrayMenu.Items = []; // FIXME: use a registry?

return SystrayMenu;

});
