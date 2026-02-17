import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { normalize } from "@web/core/l10n/utils";
import { ProductTemplate } from "./product_template";

// When adding a method to this class, please pay attention to naming.
// As in the backend, when trying to access taxes_id on product.product,
// taxes_id will be taken from the template.

// This means that if you declare a method that exists in the product.template
// class, it will override this path.
export class ProductProduct extends Base {
    static pythonModel = "product.product";
    static enableLazyGetters = false;
    static setupFn = enhanceProductTemplate;

    setup(_vals) {
        super.setup(_vals);
        this._searchString = null;
        this.product_tmpl_id?.onUpdate(); // To invalidate the searchString of the template
    }

    getImageUrl() {
        return `/web/image?model=product.product&field=image_128&id=${this.id}&unique=${this.write_date}`;
    }

    get searchString() {
        if (this._searchString) {
            return this._searchString;
        }
        const fields = ["display_name", "barcode", "default_code"];
        const raw = fields
            .map((field) => this[field] || "")
            .filter(Boolean)
            .join(" ");
        this._searchString = normalize(raw);
        return this._searchString;
    }
}

export function enhanceProductTemplate() {
    // This mimics the Odoo delegation inheritance between product.product and product.template,
    // where accessing an undefined field/method on a product transparently falls through to its template.

    let proto = ProductTemplate.prototype;
    while (proto && proto !== Object.prototype) {
        for (const name of Object.getOwnPropertyNames(proto)) {
            if (name === "constructor") {
                continue;
            }
            if (name in ProductProduct.prototype) {
                continue;
            }

            const desc = Object.getOwnPropertyDescriptor(proto, name);
            if (!desc) {
                continue;
            }
            if (typeof desc.value === "function") {
                Object.defineProperty(ProductProduct.prototype, name, {
                    value: function (...args) {
                        return this.product_tmpl_id?.[name]?.call(this, ...args);
                    },
                    configurable: true,
                });
            } else if (typeof desc.get === "function") {
                const propertyDescriptor = {
                    get: function () {
                        return this.product_tmpl_id?.[name];
                    },
                    configurable: true,
                };
                if (typeof desc.set === "function") {
                    propertyDescriptor.set = function (value) {
                        if (this.product_tmpl_id) {
                            this.product_tmpl_id[name] = value;
                        }
                    };
                }
                Object.defineProperty(ProductProduct.prototype, name, propertyDescriptor);
            }
        }
        proto = Object.getPrototypeOf(proto);
    }
}

registry.category("pos_available_models").add(ProductProduct.pythonModel, ProductProduct);
