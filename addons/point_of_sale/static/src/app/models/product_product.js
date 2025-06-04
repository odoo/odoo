import { registry } from "@web/core/registry";
import { Base } from "./related_models";

// When adding a method to this class, please pay attention to naming.
// As in the backend, when trying to access taxes_id on product.product,
// taxes_id will be taken from the template.

// This means that if you declare a method that exists in the product.template
// class, it will override this path.
export class ProductProduct extends Base {
    static pythonModel = "product.product";

    getImageUrl() {
        return (
            (this.image_128 &&
                `/web/image?model=product.product&field=image_128&id=${this.id}&unique=${this.write_date}`) ||
            ""
        );
    }
<<<<<<< 5965317e05eb1ae42ed4311c34fbe6b9c3243a6e
||||||| 81aff3dfe17aa3fe530ff7f82740c226b3eae169

    getApplicablePricelistRules(pricelist) {
        const productTmplRules =
            this.product_tmpl_id["<-product.pricelist.item.product_tmpl_id"] || [];
        const productRules = this["<-product.pricelist.item.product_id"] || [];
        const rulesIds = [...new Set([...productTmplRules, ...productRules])].map(
            (rule) => rule.id
        );
        if (
            this.uiState.applicablePricelistRules[pricelist.id] &&
            (!rulesIds.length ||
                this.uiState.applicablePricelistRules[pricelist.id].includes(rulesIds[0]))
        ) {
            return this.uiState.applicablePricelistRules[pricelist.id];
        }

        const parentCategoryIds = this.parentCategories;
        const availableRules =
            pricelist.item_ids?.filter(
                (rule) =>
                    (rulesIds.includes(rule.id) || (!rule.product_id && !rule.product_tmpl_id)) &&
                    (!rule.product_id || rule.product_id.id === this.id) &&
                    (!rule.categ_id || parentCategoryIds.includes(rule.categ_id.id))
            ) || [];
        this.uiState.applicablePricelistRules[pricelist.id] = availableRules.map((rule) => rule.id);
        return this.uiState.applicablePricelistRules[pricelist.id];
    }
=======

    getApplicablePricelistRules(pricelist) {
        const productTmplRules =
            this.product_tmpl_id["<-product.pricelist.item.product_tmpl_id"] || [];
        const productRules = this["<-product.pricelist.item.product_id"] || [];
        const rulesIds = [...new Set([...productTmplRules, ...productRules])]
            .filter((rule) => rule.pricelist_id.id === pricelist.id)
            .map((rule) => rule.id);
        if (
            this.uiState.applicablePricelistRules[pricelist.id] &&
            (!rulesIds.length ||
                this.uiState.applicablePricelistRules[pricelist.id].includes(rulesIds[0]))
        ) {
            return this.uiState.applicablePricelistRules[pricelist.id];
        }

        const parentCategoryIds = this.parentCategories;
        const availableRules =
            pricelist.item_ids?.filter(
                (rule) =>
                    (rulesIds.includes(rule.id) || (!rule.product_id && !rule.product_tmpl_id)) &&
                    (!rule.product_id || rule.product_id.id === this.id) &&
                    (!rule.categ_id || parentCategoryIds.includes(rule.categ_id.id))
            ) || [];
        this.uiState.applicablePricelistRules[pricelist.id] = availableRules.map((rule) => rule.id);
        return this.uiState.applicablePricelistRules[pricelist.id];
    }
>>>>>>> 75f3f102999d203cfc835d5968490e3279fb60ac
}

const ProductProductTemplateProxy = new Proxy(ProductProduct, {
    construct(target, args) {
        const instance = new target(...args);
        return new Proxy(instance, {
            get(target, prop) {
                const val = Reflect.get(target, prop);

                if (val || target.model.fields[prop] || typeof prop === "symbol") {
                    return val;
                }

                return target?.product_tmpl_id?.[prop];
            },
        });
    },
});

registry
    .category("pos_available_models")
    .add(ProductProduct.pythonModel, ProductProductTemplateProxy);
