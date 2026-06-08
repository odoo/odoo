import { useExternalListener, useRef } from "@web/owl2/utils";
import { Component, props, types } from "@odoo/owl";
import { useScrollShadow } from "../../utils/scroll_shadow_hook";

export class CategoryListPopup extends Component {
    static template = "pos_self_order.CategoryListPopup";
    props = props({
        close: types.function(),
        categories: types.object(),
        onCategorySelected: types.function(),
    });

    setup() {
        this.scrollShadow = useScrollShadow(useRef("scrollContainer"));
        useExternalListener(window, "click", this.props.close);
    }

    selectCategory(cat) {
        this.props.close();
        this.props.onCategorySelected(cat);
    }
}
