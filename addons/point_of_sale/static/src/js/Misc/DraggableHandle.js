odoo.define('point_of_sale.DraggableHandle', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');

    class DraggableHandle extends PosComponent {}

    return { DraggableHandle };
});
