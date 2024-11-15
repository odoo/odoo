import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { _t } from "@web/core/l10n/translation";
import { roundPrecision } from "@web/core/utils/numbers";
import { getTaxesAfterFiscalPosition, getTaxesValues } from "./utils/tax_utils";
import { markup } from "@odoo/owl";

/**
 * ProductProduct, shadow of product.product in python.
 * To works properly, this model needs to be registered in the registry
 * with the key "pos_available_models". And to be instanciated with the
 * method createRelatedModels from related_models.js
 *
 * Models to load: product.product, uom.uom
 */

export class ProductTemplate extends Base {
    static pythonModel = "product.template";

    getProductPriceDetails(price, pricelist = false, fiscalPosition = false) {
        const config = this.models["pos.config"].getFirst();
        const productTemplate = this instanceof ProductTemplate ? this : this.product_tmpl_id;
        const basePrice = this?.lst_price || productTemplate.getPrice(pricelist, 1);
        const selectedPrice = price === undefined ? basePrice : price;

        let taxes = productTemplate.taxes_id;

        // Fiscal position.
        if (fiscalPosition) {
            taxes = getTaxesAfterFiscalPosition(taxes, fiscalPosition, this.models);
        }

        // Taxes computation.
        const taxesData = getTaxesValues(
            taxes,
            selectedPrice,
            1,
            productTemplate,
            config._product_default_values,
            config.company_id,
            config.currency_id
        );

        return taxesData;
    }

    getProductPrice(price = false, pricelist = false, fiscalPosition = false) {
        const config = this.models["pos.config"].getFirst();
        const taxesData = this.getProductPriceDetails(price, pricelist, fiscalPosition);
        if (config.iface_tax_included === "total") {
            return taxesData.total_included;
        } else {
            return taxesData.total_excluded;
        }
    }

    isAllowOnlyOneLot() {
        const productUnit = this.uom_id;
        return this.tracking === "lot" || !productUnit || !productUnit.is_pos_groupable;
    }

    isTracked() {
        const pickingType = this.models["stock.picking.type"].readAll()[0];

        return (
            ["serial", "lot"].includes(this.tracking) &&
            (pickingType.use_create_lots || pickingType.use_existing_lots)
        );
    }

    async _onScaleNotAvailable() {}

    isConfigurable() {
        return this.attribute_line_ids.find((l) => l.product_template_value_ids.length > 1);
    }

    needToConfigure() {
        return (
            this.isConfigurable() &&
            this.attribute_line_ids.length > 0 &&
            !this.attribute_line_ids.every((l) => l.attribute_id.create_variant === "always")
        );
    }

    isCombo() {
        return this.combo_ids.length;
    }

    get isScaleAvailable() {
        return true;
    }

    get parentCategories() {
        const categories = [];
        let category = this.categ_id;

        while (category) {
            categories.push(category.id);
            category = category.parent_id;
        }

        return categories;
    }

    get parentPosCategIds() {
        const current = [];
        const categories = this.pos_categ_ids;

        const getParent = (categ) => {
            if (categ.parent_id) {
                current.push(categ.parent_id.id);
                getParent(categ.parent_id);
            }
        };

        for (const category of categories) {
            current.push(category.id);
            getParent(category);
        }

        return current;
    }

    // Port of _get_product_price on product.pricelist.
    //
    // Anything related to UOM can be ignored, the POS will always use
    // the default UOM set on the product and the user cannot change
    // it.
    //
    // Pricelist items do not have to be sorted. All
    // product.pricelist.item records are loaded with a search_read
    // and were automatically sorted based on their _order by the
    // ORM. After that they are added in this order to the pricelists.
    getPrice(pricelist, quantity, price_extra = 0, recurring = false, variant = false) {
        // In case of nested pricelists, it is necessary that all pricelists are made available in
        // the POS. Display a basic alert to the user in the case where there is a pricelist item
        // but we can't load the base pricelist to get the price when calling this method again.
        // As this method is also call without pricelist available in the POS, we can't just check
        // the absence of pricelist.
        if (recurring && !pricelist) {
            alert(
                _t(
                    "An error occurred when loading product prices. " +
                        "Make sure all pricelists are available in the POS."
                )
            );
        }

        const product = variant;
        const productTmpl = variant.product_tmpl_id || this;
        const standardPrice = variant ? variant.standard_price : this.standard_price;
        const basePrice = variant ? variant.lst_price : this.list_price;
        const productTmplRules = productTmpl["<-product.pricelist.item.product_tmpl_id"] || [];
        const productRules = product["<-product.pricelist.item.product_id"] || [];
        const rulesIds = [...productTmplRules, ...productRules].map((rule) => rule.id);

        let price = basePrice + (price_extra || 0);
        const rules =
            pricelist?.item_ids?.filter(
                (rule) =>
                    (rulesIds.includes(rule.id) || (!rule.product_id && !rule.product_tmpl_id)) &&
                    (!rule.min_quantity || quantity >= rule.min_quantity) &&
                    (!rule.product_id || rule.product_id.id === product?.id) &&
                    (!rule.categ_id || rule.categ_id.id === product?.categ_id?.id)
            ) || [];

        // We take in first assigned product rules instead of common one.
        let commonRule = "";
        let productVariantRule = "";
        let productTemplateRule = "";
        for (const rule of rules) {
            if (!rule.product_id && !rule.product_tmpl_id) {
                commonRule = rule;
            }
            if (rule.product_id?.id === product?.id) {
                productVariantRule = rule;
                break;
            }
            if (rule.product_tmpl_id?.id === productTmpl.id) {
                productTemplateRule = rule;
            }
        }

        const rule = productVariantRule || productTemplateRule || commonRule;
        if (!rule) {
            return price;
        }
        if (rule.base === "pricelist") {
            if (rule.base_pricelist_id) {
                price = this.getPrice(rule.base_pricelist_id, quantity, 0, true, variant);
            }
        } else if (rule.base === "standard_price") {
            price = standardPrice;
        }

        if (rule.compute_price === "fixed") {
            price = rule.fixed_price;
        } else if (rule.compute_price === "percentage") {
            price = price - price * (rule.percent_price / 100);
        } else {
            var price_limit = price;
            price -= price * (rule.price_discount / 100);
            if (rule.price_round) {
                price = roundPrecision(price, rule.price_round);
            }
            if (rule.price_surcharge) {
                price += rule.price_surcharge;
            }
            if (rule.price_min_margin) {
                price = Math.max(price, price_limit + rule.price_min_margin);
            }
            if (rule.price_max_margin) {
                price = Math.min(price, price_limit + rule.price_max_margin);
            }
        }

        // This return value has to be rounded with round_di before
        // being used further. Note that this cannot happen here,
        // because it would cause inconsistencies with the backend for
        // pricelist that have base == 'pricelist'.
        return price;
    }

    getImageUrl() {
        return (
            (this.image_128 &&
                `/web/image?model=product.template&field=image_128&id=${this.id}&unique=${this.write_date}`) ||
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

    get productDescriptionMarkup() {
        return this.public_description ? markup(this.public_description) : "";
    }
}
registry.category("pos_available_models").add(ProductTemplate.pythonModel, ProductTemplate);
