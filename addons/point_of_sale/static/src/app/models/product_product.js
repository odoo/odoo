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
<<<<<<< master
||||||| 204fbd00019c655e4becbef66ab235229166a468

    getTemplateImageUrl() {
        return (
            (this.image_128 &&
                `/web/image?model=product.template&field=image_128&id=${this.raw.product_tmpl_id}&unique=${this.write_date}`) ||
            ""
        );
    }

    get searchString() {
        const fields = ["display_name", "description_sale", "description"];
        return fields
            .map((field) => this[field] || "")
            .filter(Boolean)
            .join(" ");
    }

    exactMatch(searchWord) {
        const fields = ["barcode", "default_code"];
        return fields.some((field) => this[field] && this[field].includes(searchWord));
    }

    _isArchivedCombination(attributeValueIds) {
        if (!this._archived_combinations) {
            return false;
        }
        const excludedPTAV = new Set();
        let isCombinationArchived = false;
        for (const archivedCombination of this._archived_combinations) {
            const ptavCommon = archivedCombination.filter((ptav) =>
                attributeValueIds.includes(ptav)
            );
            if (ptavCommon.length === attributeValueIds.length) {
                // all attributes must be disabled from each other
                archivedCombination.forEach((ptav) => excludedPTAV.add(ptav));
            } else if (ptavCommon.length === attributeValueIds.length - 1) {
                // In this case we only need to disable the remaining ptav
                const disablePTAV = archivedCombination.find(
                    (ptav) => !attributeValueIds.includes(ptav)
                );
                excludedPTAV.add(disablePTAV);
            }
            if (ptavCommon.length === attributeValueIds.length) {
                isCombinationArchived = true;
            }
        }
        this.attribute_line_ids.forEach((attribute_line) => {
            attribute_line.product_template_value_ids.forEach((ptav) => {
                ptav["excluded"] = excludedPTAV.has(ptav.id);
            });
        });
        return isCombinationArchived;
    }
=======

    getTemplateImageUrl() {
        return (
            (this.image_128 &&
                `/web/image?model=product.template&field=image_128&id=${this.raw.product_tmpl_id}&unique=${this.write_date}`) ||
            ""
        );
    }

    get searchString() {
        const fields = ["display_name", "description_sale", "description"];
        return fields
            .map((field) => this[field] || "")
            .filter(Boolean)
            .join(" ");
    }

    exactMatch(searchWord) {
        const fields = ["barcode", "default_code"];
        return fields.some((field) => this[field] && this[field].includes(searchWord));
    }

    _isArchivedCombination(attributeValueIds) {
        if (!this._archived_combinations) {
            return false;
        }
        const excludedPTAV = new Set();
        let isCombinationArchived = false;
        for (const archivedCombination of this._archived_combinations) {
            const ptavCommon = archivedCombination.filter((ptav) =>
                attributeValueIds.includes(ptav)
            );
            if (ptavCommon.length === attributeValueIds.length) {
                // all attributes must be disabled from each other
                archivedCombination.forEach((ptav) => excludedPTAV.add(ptav));
            } else if (ptavCommon.length === attributeValueIds.length - 1) {
                // In this case we only need to disable the remaining ptav
                const disablePTAV = archivedCombination.find(
                    (ptav) => !attributeValueIds.includes(ptav)
                );
                excludedPTAV.add(disablePTAV);
            }
            if (ptavCommon.length === attributeValueIds.length) {
                isCombinationArchived = true;
            }
        }
        this.attribute_line_ids.forEach((attribute_line) => {
            attribute_line.product_template_value_ids.forEach((ptav) => {
                ptav["excluded"] = excludedPTAV.has(ptav.id);
            });
        });
        return isCombinationArchived;
    }

    get productDisplayName() {
        return this.default_code ? `[${this.default_code}] ${this.name}` : this.name;
    }
>>>>>>> a592f2433588a00c3d06ecdcd0749933df8b4db7
}

const ProductProductTemplateProxy = new Proxy(ProductProduct, {
    construct(target, args) {
        const instance = new target(...args);
        return new Proxy(instance, {
            get(target, prop) {
                const val = Reflect.get(target, prop);

                if (val || target.model.modelFields[prop] || typeof prop === "symbol") {
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
