import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class PosCategory extends Base {
    static pythonModel = "pos.category";

    getAllChildren() {
        const children = [this];
        if (this.child_ids.length === 0) {
            return children;
        }
        for (const child of this.child_ids) {
            children.push(...child.getAllChildren());
        }
        return children;
    }

    get allParents() {
        const parents = [];
        let parent = this.parent_id;

        if (!parent) {
            return parents;
        }

        while (parent) {
            parents.unshift(parent);
            parent = parent.parent_id;
        }

        return parents.reverse();
    }
    get associatedProducts() {
        const allCategoryIds = this.getAllChildren().map((cat) => cat.id);
        const products = allCategoryIds.flatMap(
            (catId) => this.models["product.template"].getBy("pos_categ_ids", catId) || []
        );
        // Remove duplicates since owl doesn't like them.
        return Array.from(new Set(products));
    }

    get hasProductsToShow() {
        return this.associatedProducts.length > 0;
    }
}

registry.category("pos_available_models").add(PosCategory.pythonModel, PosCategory);
