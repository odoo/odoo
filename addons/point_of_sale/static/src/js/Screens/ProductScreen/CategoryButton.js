odoo.define('point_of_sale.CategoryButton', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');

    class CategoryButton extends PosComponent {
        get imageUrl() {
            return `${window.location.origin}/web/image?model=pos.category&field=image_128&id=${this.props.category.id}`;
        }
    }

    return { CategoryButton }
});
