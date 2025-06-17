import { registry } from "@web/core/registry";
import { Base } from "./related_models";

// When adding a method to this class, please pay attention to naming.
// As in the backend, when trying to access taxes_id on product.product,
// taxes_id will be taken from the template.

// This means that if you declare a method that exists in the product.template
// class, it will override this path.
export class ProductProduct extends Base {
    static pythonModel = "product.product";

    setup() {
        super.setup(...arguments);
        this.uiState = {
            applicablePricelistRules: {},
        };
    }

    getImageUrl() {
        return (
            (this.image_128 &&
                `/web/image?model=product.product&field=image_128&id=${this.id}&unique=${this.write_date}`) ||
            ""
        );
    }

    getApplicablePricelistRules(pricelist) {
        const filter = (r) => r.pricelist_id.id === pricelist.id;
        const tmpl = this.product_tmpl_id;
        const rules = (tmpl["<-product.pricelist.item.product_tmpl_id"] || []).filter(filter);
        const productRules = (this["<-product.pricelist.item.product_id"] || []).filter(filter);
        const rulesSet = new Set([...rules.map((r) => r.id), ...productRules.map((r) => r.id)]);

        if (this.uiState.applicablePricelistRules[pricelist.id] && !rulesSet.size) {
            return this.uiState.applicablePricelistRules[pricelist.id];
        }

        const generalRules = pricelist.getGeneralRulesByCategories(this.parentCategories);

        this.uiState.applicablePricelistRules[pricelist.id] = [
            ...rulesSet,
            ...generalRules.map((rule) => rule.id),
        ];

        return this.uiState.applicablePricelistRules[pricelist.id];
    }
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
