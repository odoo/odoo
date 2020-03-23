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
        this.Items = SystrayMenu.Items.slice().sort((ItemA, ItemB) => {
            const seqA = ItemA.prototype.sequence !== undefined ? ItemA.prototype.sequence : 50;
            const seqB = ItemB.prototype.sequence !== undefined ? ItemB.prototype.sequence : 50;
            return seqA < seqB;
        });
    }
}
SystrayMenu.components = { ItemAdapter, UserMenu };
SystrayMenu.template = 'web.SystrayMenu';
SystrayMenu.Items = []; // FIXME: use a registry?

return SystrayMenu;

});
