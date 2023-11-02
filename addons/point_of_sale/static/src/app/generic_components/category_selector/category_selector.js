/** @odoo-module */

import { Component } from "@odoo/owl";

/**
 * @typedef {Object} Category
 * @property {number} id
 * @property {string?} name
 * @property {string?} icon
 * @property {string?} separator
 * @property {string?} imageUrl
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
                separator: { type: String, optional: true },
                imageUrl: { type: String, optional: true },
            },
        },
        class: { type: String, optional: true },
        showImage: { type: Boolean, optional: true },
        onClick: { type: Function },
    };
    static defaultProps = {
        class: "",
        showImage: true,
    };
}
