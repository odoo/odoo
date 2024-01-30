/** @odoo-module */

import { Component } from "@odoo/owl";

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
                icon: { type: String, optional: true },
                showSeparator: { type: Boolean, optional: true },
                has_image: Boolean,
                color: { type: Number, optional: true },
            },
        },
        class: { type: String, optional: true },
        onClick: { type: Function },
        getImgSrc: { type: Function, optional: true },
    };
    static defaultProps = {
        class: "",
        getImgSrc: (c) => `/web/image?model=pos.category&field=image_128&id=${c.id}`,
    };
}
