/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { CategorySelector } from "@point_of_sale/app/generic_components/category_selector/category_selector";


patch(CategorySelector, {
    props: { ...CategorySelector.props, getEventSelected: { type: Function } },
});
