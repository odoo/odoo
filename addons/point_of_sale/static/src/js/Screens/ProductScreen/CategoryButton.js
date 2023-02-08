/** @odoo-module */

import { LegacyComponent } from "@web/legacy/legacy_component";

export class CategoryButton extends LegacyComponent {
    static template = "CategoryButton";

    get imageUrl() {
        const category = this.props.category;
        return `/web/image?model=pos.category&field=image_128&id=${category.id}&unique=${category.write_date}`;
    }
}
