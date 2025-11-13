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

    get searchString() {
        const fields = ["display_name", "barcode", "default_code"];
        return fields
            .map((field) => this[field] || "")
            .filter(Boolean)
            .join(" ");
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
