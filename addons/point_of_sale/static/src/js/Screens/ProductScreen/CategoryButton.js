/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

class CategoryButton extends PosComponent {
    get imageUrl() {
        const category = this.props.category;
        return `/web/image?model=pos.category&field=image_128&id=${category.id}&unique=${category.write_date}`;
    }
}
CategoryButton.template = "CategoryButton";

Registries.Component.add(CategoryButton);

export default CategoryButton;
