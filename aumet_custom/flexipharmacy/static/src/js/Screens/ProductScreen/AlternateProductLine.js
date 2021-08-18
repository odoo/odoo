odoo.define('flexipharmacy.AlternateProductLine', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    var rpc = require('web.rpc');
    const { useState } = owl.hooks;

    class AlternateProductLine extends PosComponent {
        constructor() {
            super(...arguments);
        }
        spaceClickProduct(event) {
            if (event.which === 32) {
                this.trigger('click-alternate-product', this.env.pos.db.get_product_by_id(props.alternate_product_id));
            }
        }
        get imageUrl() {
            const lines = this.env.pos.db.get_product_by_id(this.props.alternate_product_id);
            return `/web/image?model=product.product&field=image_128&id=${lines.id}&write_date=${lines.write_date}&unique=1`;
        }
    } 

    AlternateProductLine.template = 'AlternateProductLine';

    Registries.Component.add(AlternateProductLine);

    return AlternateProductLine;
});
