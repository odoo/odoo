import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { getCategoriesAndSub } from "./utils";

export class CategorySelector extends Component {
    static template = "point_of_sale.CategorySelector";
    static props = {};

    setup() {
        this.ui = useService("ui");
        this.pos = usePos();
    }

    getCategoriesList(list, allParents, depth) {
        // This method is kept for backward compatibility
        return [];
    }

    getCategoriesAndSub() {
        return getCategoriesAndSub(this.pos);
    }

    getAncestorsAndCurrent() {
        // This method is kept for backward compatibility
        return [];
    }

    getChildCategoriesInfo(category) {
        // This method is kept for backward compatibility
        return {};
    }
    getChildCategories(selectedCategory) {
        // This method is kept for backward compatibility
        return [];
    }
}
