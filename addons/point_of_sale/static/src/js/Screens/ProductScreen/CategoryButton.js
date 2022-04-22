odoo.define('point_of_sale.CategoryButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class CategoryButton extends PosComponent {
        get imageUrl() {
            const category = this.props.category
            return `/web/image?model=pos.category&field=image_128&id=${category.id}&unique=${category.write_date}`;
        }
    }
    CategoryButton.template = 'CategoryButton';

    Registries.Component.add(CategoryButton);

    return CategoryButton;
});
