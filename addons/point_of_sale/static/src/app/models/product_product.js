import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { _t } from "@web/core/l10n/translation";
import { roundPrecision } from "@web/core/utils/numbers";

/**
 * ProductProduct, shadow of product.product in python.
 * To works properly, this model needs to be registered in the registry
 * with the key "pos_available_models". And to be instanciated with the
 * method createRelatedModels from related_models.js
 *
 * Models to load: product.product, uom.uom
 */

export class ProductProduct extends Base {
    static pythonModel = "product.product";

    constructor() {
        super(...arguments);
        this.cachedPricelistRules = {};
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
        return this.attribute_line_ids.map((a) => a.product_template_value_ids).flat().length > 1;
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

    getApplicablePricelistRules(pricelistRules) {
        const applicableRules = {};
        for (const pricelistId in pricelistRules) {
            applicableRules[pricelistId] = [];
            const rules = pricelistRules[pricelistId];
            if (rules.productItems[this.id]) {
                applicableRules[pricelistId].push(...rules.productItems[this.id]);
                if (!rules.productItems[this.id][0].min_quantity) {
                    continue;
                }
            }
            const productTmplId = this.raw.product_tmpl_id;
            if (rules.productTmlpItems[productTmplId]) {
                applicableRules[pricelistId].push(...rules.productTmlpItems[productTmplId]);
                if (!rules.productTmlpItems[productTmplId][0].min_quantity) {
                    continue;
                }
            }
            for (const category of this.parentCategories) {
                if (rules.categoryItems[category]) {
                    applicableRules[pricelistId].push(...rules.categoryItems[category]);
                    if (!rules.categoryItems[category][0].min_quantity) {
                        break;
                    }
                }
            }
            applicableRules[pricelistId].push(...rules.globalItems);
        }
        return applicableRules;
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
    get_price(pricelist, quantity, price_extra = 0, recurring = false, list_price = false) {
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

        let price = (list_price || this.lst_price) + (price_extra || 0);
        const rule = this.getPricelistRule(pricelist, quantity);
        if (!rule) {
            return price;
        }

        if (rule.base === "pricelist") {
            if (rule.base_pricelist_id) {
                price = this.get_price(rule.base_pricelist_id, quantity, 0, true, list_price);
            }
        } else if (rule.base === "standard_price") {
            price = this.standard_price;
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

    getPricelistRule(pricelist, quantity) {
        const rules = !pricelist ? [] : this.cachedPricelistRules[pricelist?.id] || [];
        return rules.find((rule) => !rule.min_quantity || quantity >= rule.min_quantity);
    }
    getImageUrl() {
        return (
            (this.image_128 &&
                `/web/image?model=product.product&field=image_128&id=${this.id}&unique=${this.write_date}`) ||
            ""
        );
    }

    getTemplateImageUrl() {
        return (
            (this.image_128 &&
                `/web/image?model=product.template&field=image_128&id=${this.raw.product_tmpl_id}&unique=${this.write_date}`) ||
            ""
        );
    }

    get searchString() {
        const fields = ["display_name"];
        return fields
            .map((field) => this[field] || "")
            .filter(Boolean)
            .join(" ");
    }

    exactMatch(searchWord) {
        const fields = ["barcode", "default_code"];
        return fields.some((field) => this[field] && this[field].toLowerCase() == searchWord);
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
    get canBeDisplayed() {
        return this.active && this.available_in_pos;
    }
}
registry.category("pos_available_models").add(ProductProduct.pythonModel, ProductProduct);
