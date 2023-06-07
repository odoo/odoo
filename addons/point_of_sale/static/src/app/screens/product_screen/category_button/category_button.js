/** @odoo-module */

import { Component } from "@odoo/owl";

export class CategoryButton extends Component {
    static template = "point_of_sale.CategoryButton";

    get imageUrl() {
        const category = this.props.category;
        return `/web/image?model=pos.category&field=image_128&id=${category.id}&unique=${category.write_date}`;
    }
}
