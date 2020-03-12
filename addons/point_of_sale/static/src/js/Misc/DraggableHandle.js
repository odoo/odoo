odoo.define('point_of_sale.DraggableHandle', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class DraggableHandle extends PosComponent {
        static template = 'DraggableHandle';
    }

    Registry.add('DraggableHandle', DraggableHandle);

    return { DraggableHandle };
});
