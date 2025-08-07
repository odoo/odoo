import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { _t } from "@web/core/l10n/translation";
import { roundPrecision } from "@web/core/utils/numbers";
import { markup } from "@odoo/owl";
import { getTaxesAfterFiscalPosition, getTaxesValues } from "./utils/tax_utils";
import { accountTaxHelpers } from "@account/helpers/account_tax";

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

    prepareProductBaseLineForTaxesComputationExtraValues(
        price,
        pricelist = false,
        fiscalPosition = false
    ) {
        const config = this.models["pos.config"].getFirst();
        const productTemplate = this instanceof ProductTemplate ? this : this.product_tmpl_id;
        const basePrice = this?.lst_price || productTemplate.getPrice(pricelist, 1);
        const priceUnit = price || price === 0 ? price : basePrice;
        const currency = config.currency_id;
        const extraValues = { currency_id: currency };

        let taxes = this.taxes_id;

        // Fiscal position.
        if (fiscalPosition) {
            taxes = getTaxesAfterFiscalPosition(taxes, fiscalPosition, this.models);
        }

        return {
            ...extraValues,
            product_id: this,
            quantity: 1,
            price_unit: priceUnit,
            tax_ids: taxes,
        };
    }

    getProductPrice(price = false, pricelist = false, fiscalPosition = false) {
        const config = this.models["pos.config"].getFirst();
        const baseLine = accountTaxHelpers.prepare_base_line_for_taxes_computation(
            {},
            this.prepareProductBaseLineForTaxesComputationExtraValues(
                price,
                pricelist,
                fiscalPosition
            )
        );
        accountTaxHelpers.add_tax_details_in_base_line(baseLine, config.company_id);
        accountTaxHelpers.round_base_lines_tax_details([baseLine], config.company_id);

        if (config.iface_tax_included === "total") {
            return baseLine.tax_details.total_included_currency;
        } else {
            return baseLine.tax_details.total_excluded_currency;
        }
    }
    getProductPriceInfo(product, company, pricelist = false, fiscalPosition = false) {
        if (!product) {
            product = this.product_variant_ids[0];
        }
        const price = this.getPrice(pricelist, 1, 0, false, product);

        const extraValues = this.prepareProductBaseLineForTaxesComputationExtraValues(
            price,
            pricelist,
            fiscalPosition
        );

        // Taxes computation.
        const taxesData = getTaxesValues(
            extraValues.tax_ids,
            extraValues.price_unit,
            extraValues.quantity,
            product,
            extraValues.product_id,
            company,
            extraValues.currency_id
        );

        return taxesData;
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
            this.attribute_line_ids.some((l) => l.attribute_id.create_variant === "no_variant")
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

    getApplicablePricelistRules(pricelist) {
        const filter = (r) => r.pricelist_id.id === pricelist.id;
        const rules = (this["<-product.pricelist.item.product_tmpl_id"] || [])
            .filter(filter)
            .sort((a, b) => b.min_quantity - a.min_quantity);
        const rulesSet = new Set(rules.map((r) => r.id));
        const generalRulesIds = pricelist.getGeneralRulesIdsByCategories(this.parentCategories);
        return [...rulesSet, ...generalRulesIds];
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
        const standardPrice = variant ? variant.standard_price : this.standard_price;
        const basePrice = variant ? variant.lst_price : this.list_price;
        let price = basePrice + (price_extra || 0);
        let rules = [];
        if (pricelist) {
            if (product) {
                rules = product.getApplicablePricelistRules(pricelist);
            } else {
                rules = this.getApplicablePricelistRules(pricelist);
            }
            rules = this.models["product.pricelist.item"].readMany(rules);
            rules = rules.filter((rule) => !rule.min_quantity || quantity >= rule.min_quantity);
        }

        const rule = rules.length && rules[0];
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
        const fields = ["display_name", "default_code"];
        return fields
            .map((field) => this[field] || "")
            .filter(Boolean)
            .join(" ");
    }

    exactMatch(searchWord) {
        const fields = ["barcode"];
        const variantMatch = this.product_variant_ids.some(
            (variant) =>
                (variant.barcode && variant.barcode.toLowerCase() == searchWord) ||
                variant.product_template_variant_value_ids.some((vv) =>
                    vv.name.toLowerCase().includes(searchWord)
                )
        );
        return (
            variantMatch ||
            fields.some((field) => this[field] && this[field].toLowerCase() == searchWord)
        );
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

    get canBeDisplayed() {
        return this.active && this.available_in_pos;
    }
}
registry.category("pos_available_models").add(ProductTemplate.pythonModel, ProductTemplate);
