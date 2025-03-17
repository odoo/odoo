import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";

export class CategorySelector extends Component {
    static template = "point_of_sale.CategorySelector";
    static props = {};

    setup() {
        this.ui = useService("ui");
        this.pos = usePos();
    }

    getCategoriesList(list, allParents, depth) {
        const categoriesList = [...list];
        list.forEach((item) => {
            if (item.id === allParents[depth]?.id && item.child_ids?.length) {
                categoriesList.push(
                    ...this.getCategoriesList(item.child_ids, allParents, depth + 1)
                );
            }
        });
        return categoriesList;
    }

    getCategoriesAndSub() {
        const rootCategories = this.pos.models["pos.category"].filter(
            (category) => !category.parent_id
        );
        const selected = this.pos.selectedCategory ? [this.pos.selectedCategory] : [];
        const allParents = selected.concat(this.pos.selectedCategory?.allParents || []).reverse();
        return this.getCategoriesList(rootCategories, allParents, 0)
            .flat(Infinity)
            .map(this.getChildCategoriesInfo, this);
    }

    getAncestorsAndCurrent() {
        const selectedCategory = this.pos.selectedCategory;
        return selectedCategory
            ? [undefined, ...selectedCategory.allParents, selectedCategory]
            : [selectedCategory];
    }

    getChildCategoriesInfo(category) {
        return {
            ...pick(category, "id", "name", "color"),
            imgSrc:
                this.pos.config.show_category_images && category.has_image
                    ? `/web/image?model=pos.category&field=image_128&id=${category.id}`
                    : undefined,
            isSelected: this.getAncestorsAndCurrent().includes(category),
            isChildren: this.getChildCategories(this.pos.selectedCategory).includes(category),
        };
    }

    getChildCategories(selectedCategory) {
        return selectedCategory
            ? [...selectedCategory.child_ids]
            : this.pos.models["pos.category"].filter((category) => !category.parent_id);
    }
}
