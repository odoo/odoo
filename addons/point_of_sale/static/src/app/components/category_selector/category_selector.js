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
            if (item.id === allParents[depth]?.id) {
                const children = this.getChildren(item);
                if (children.length) {
                    categoriesList.push(...this.getCategoriesList(children, allParents, depth + 1));
                }
            }
        });
        return categoriesList;
    }

    getCategoriesAndSub() {
        const { limit_categories, iface_available_categ_ids } = this.pos.config;
        let displayableCategories;
        if (limit_categories && iface_available_categ_ids.length > 0) {
            displayableCategories = iface_available_categ_ids;
            const allowedIdSet = new Set(displayableCategories.map((c) => c.id));
            this.isAllowedCategory = (category) => allowedIdSet.has(category.id);
        } else {
            displayableCategories = this.pos.models["pos.category"].getAll();
            this.isAllowedCategory = () => true;
        }

        const rootCategories = displayableCategories
            .filter(
                (category) => !category.parent_id || !this.isAllowedCategory(category.parent_id)
            )
            .sort((a, b) => a.sequence - b.sequence);
        const selected = this.pos.selectedCategory ? [this.pos.selectedCategory] : [];
        const allParents = selected.concat(this.getAllParents(this.pos.selectedCategory)).reverse();
        const result = this.getCategoriesList(rootCategories, allParents, 0)
            .flat(Infinity)
            .filter((c) => c.hasProductsToShow)
            .map((c) => this.getChildCategoriesInfo(c, rootCategories));
        this.isAllowedCategory = null;
        return result;
    }

    getAncestorsAndCurrent() {
        const selectedCategory = this.pos.selectedCategory;
        return selectedCategory
            ? [undefined, ...this.getAllParents(selectedCategory), selectedCategory]
            : [selectedCategory];
    }

    getChildCategoriesInfo(category, rootCategories) {
        return {
            ...pick(category, "id", "name", "color"),
            imgSrc:
                this.pos.config.show_category_images && category.has_image
                    ? `/web/image?model=pos.category&field=image_128&id=${category.id}`
                    : undefined,
            isSelected: this.getAncestorsAndCurrent().includes(category),
            isChildren: this.getChildCategories(this.pos.selectedCategory, rootCategories).includes(
                category
            ),
        };
    }

    getChildCategories(selectedCategory, rootCategories) {
        return selectedCategory ? this.getChildren(selectedCategory) : rootCategories;
    }

    getChildren(category) {
        return (
            category.child_ids
                ?.filter((child) => this.isAllowedCategory(child))
                .sort((a, b) => a.sequence - b.sequence) || []
        );
    }

    getAllParents(category) {
        return category?.allParents.filter((cat) => this.isAllowedCategory(cat)) || [];
    }
}
