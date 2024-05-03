import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Category
 * @property {number} id
 * @property {string?} name
 * @property {string?} icon
 * @property {string?} separator
 */
export class CategorySelector extends Component {
    static template = "point_of_sale.CategorySelector";
    static props = {
        categories: {
            type: Array,
            element: Object,
            shape: {
                id: Number,
                name: { type: String, optional: true },
                color: { type: Number, optional: true },
                imgSrc: String,
                icon: { type: String, optional: true },
                showSeparator: { type: Boolean, optional: true },
                isSelected: { type: Boolean, optional: true },
                isChildren: { type: Boolean, optional: true },
            },
        },
        class: { type: String, optional: true },
        style: { type: String, optional: true },
        onClick: { type: Function },
    };
    static defaultProps = {
        class: "",
        style: "",
    };
    setup() {
        this.ui = useService("ui");
    }
}
