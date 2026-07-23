import { Component, signal, t, useListener, useProps } from "@odoo/owl";
import { useScrollShadow } from "../../utils/scroll_shadow_hook";

export class CategoryListPopup extends Component {
    static template = "pos_self_order.CategoryListPopup";
    props = useProps({
        close: t.function(),
        categories: t.object(),
        onCategorySelected: t.function(),
    });

    scrollContainerRef = signal(null);

    setup() {
        this.scrollShadow = useScrollShadow(this.scrollContainerRef);
        useListener(window, "click", this.props.close);
    }

    selectCategory(cat) {
        this.props.close();
        this.props.onCategorySelected(cat);
    }
}
