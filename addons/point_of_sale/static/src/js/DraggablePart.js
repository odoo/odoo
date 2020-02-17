odoo.define('point_of_sale.DraggablePart', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');

    class DraggablePart extends PosComponent {}

    return { DraggablePart };
});
