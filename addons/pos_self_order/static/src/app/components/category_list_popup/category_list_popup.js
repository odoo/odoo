import { useExternalListener } from "@web/owl2/utils";
import { Component, signal } from "@odoo/owl";
import { useScrollShadow } from "../../utils/scroll_shadow_hook";

export class CategoryListPopup extends Component {
    static template = "pos_self_order.CategoryListPopup";
    static props = {
        close: Function,
        categories: Object,
        onCategorySelected: Function,
    };

    scrollContainerRef = signal(null);

    setup() {
        this.scrollShadow = useScrollShadow(this.scrollContainerRef);
        useExternalListener(window, "click", this.props.close);
    }

    selectCategory(cat) {
        this.props.close();
        this.props.onCategorySelected(cat);
    }
}
