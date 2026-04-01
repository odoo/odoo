import { Component, useExternalListener, useRef } from "@odoo/owl";
import { useScrollShadow } from "../../utils/scroll_shadow_hook";

export class CategoryListPopup extends Component {
    static template = "pos_self_order.CategoryListPopup";
    static props = {
        close: Function,
        categories: Object,
        onCategorySelected: Function,
    };

    setup() {
        this.scrollShadow = useScrollShadow(useRef("scrollContainer"));
        useExternalListener(window, "click", this.props.close);
    }

    selectCategory(cat) {
        this.props.close();
        this.props.onCategorySelected(cat);
    }
}
