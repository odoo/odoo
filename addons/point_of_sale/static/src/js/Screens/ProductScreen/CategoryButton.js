/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";

export class CategoryButton extends PosComponent {
    static template = "CategoryButton";

    get imageUrl() {
        const category = this.props.category;
        return `/web/image?model=pos.category&field=image_128&id=${category.id}&unique=${category.write_date}`;
    }
}
