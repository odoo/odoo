import { useRef } from "@web/owl2/utils";
import { Component, useListener, props, t } from "@odoo/owl";
import { useScrollShadow } from "../../utils/scroll_shadow_hook";

export class CategoryListPopup extends Component {
    static template = "pos_self_order.CategoryListPopup";
    props = props({
        close: t.function(),
        categories: t.object(),
        onCategorySelected: t.function(),
    });

    setup() {
        this.scrollShadow = useScrollShadow(useRef("scrollContainer"));
        useListener(window, "click", this.props.close);
    }

    selectCategory(cat) {
        this.props.close();
        this.props.onCategorySelected(cat);
    }
}
