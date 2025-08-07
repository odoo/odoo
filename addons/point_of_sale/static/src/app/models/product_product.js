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

    getApplicablePricelistRules(pricelist) {
        const tmpl = this.product_tmpl_id;
        const tmplRules = (tmpl["<-product.pricelist.item.product_tmpl_id"] || [])
            .filter((rule) => rule.pricelist_id.id === pricelist.id && !rule.product_id)
            .sort((a, b) => b.min_quantity - a.min_quantity);
        const productRules = (this["<-product.pricelist.item.product_id"] || [])
            .filter((rule) => rule.pricelist_id.id === pricelist.id)
            .sort((a, b) => b.min_quantity - a.min_quantity);

        const tmplRulesSet = new Set(tmplRules.map((rule) => rule.id));
        const productRulesSet = new Set(productRules.map((rule) => rule.id));
        const generalRulesIds = pricelist.getGeneralRulesIdsByCategories(this.parentCategories);
        return [...productRulesSet, ...tmplRulesSet, ...generalRulesIds];
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
