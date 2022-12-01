/** @odoo-module alias=pos_event.DB */
'use strict';

import PosDB from 'point_of_sale.DB';

const super_isProductDisplayable = PosDB.prototype._isProductDisplayable;
PosDB.include({
    //@override
    _isProductDisplayable(product) {
        return super_isProductDisplayable.apply(this, arguments) && product.detailed_type !== 'event';
    }
});
