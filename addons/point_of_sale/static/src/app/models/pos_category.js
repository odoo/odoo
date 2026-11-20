import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class PosCategory extends Base {
    static pythonModel = "pos.category";
    static excludedLazyGetters = ["hasProductsToShow"];

    get children() {
        return [...this.child_ids].sort((a, b) => a.sequence - b.sequence);
    }

    getAllChildren() {
        const children = [this];
        for (const child of this.children) {
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
        const seen = new Set();
        const products = [];

        const productTemplateModel = this.models["product.template"].toRaw();
        for (const catId of allCategoryIds) {
            const catProducts = productTemplateModel.getBy("pos_categ_ids", catId);
            if (!catProducts) {
                continue;
            }
            for (const product of catProducts) {
                if (!seen.has(product.id)) {
                    seen.add(product.id);
                    products.push(product);
                }
            }
        }

        return products;
    }

    get hasProductsToShow() {
        return this.associatedProducts.length > 0;
    }
}

registry.category("pos_available_models").add(PosCategory.pythonModel, PosCategory);
