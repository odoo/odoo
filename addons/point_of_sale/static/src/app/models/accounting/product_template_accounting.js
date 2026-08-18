import { roundPrecision } from "@web/core/utils/numbers";
import { Base } from "../related_models";
import { accountTaxHelpers } from "@account/helpers/account_tax";
import { _t } from "@web/core/l10n/translation";
import { formatCurrency } from "@web/core/currency";

export class ProductTemplateAccounting extends Base {
    static pythonModel = "product.template";

    get config() {
        return this.models["pos.config"].get(odoo.pos_config_id);
    }

    prepareProductBaseLineForTaxesComputationExtraValues(opts = {}) {
        const { price = false, pricelist = false, fiscalPosition = false, priceExtra = 0 } = opts;
        const isVariant = Boolean(this?.product_tmpl_id);
        const productTemplate = isVariant ? this.product_tmpl_id : this;
        const baseP = productTemplate.getPrice(
            pricelist,
            1,
            priceExtra,
            false,
            isVariant ? this : false
        );
        const priceUnit = price || price === 0 ? price : baseP;
        const currency = this.config.currency_id;

        let taxes = this.taxes_id;

        // Fiscal position.
        if (fiscalPosition) {
            taxes = fiscalPosition.getTaxesAfterFiscalPosition(taxes);
        }

        return {
            currency_id: currency,
            product_id: this,
            quantity: 1,
            price_unit: priceUnit,
            tax_ids: taxes,
            ...opts,
        };
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
    getPrice(
        pricelist,
        quantity,
        price_extra = 0,
        recurring = false,
        variant = false,
        original_line = false,
        related_lines = []
    ) {
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
        let price = basePrice + (price_extra || 0);

        if (!pricelist) {
            return price;
        }

        if (original_line && original_line.isLotTracked() && product) {
            related_lines.push(
                ...original_line.order_id.lines.filter((line) => line.product_id.id == product.id)
            );
            quantity = related_lines.reduce((sum, line) => sum + line.getQuantity(), 0);
        }

        let rule = null;

        // 1. Variant Rules
        if (product) {
            const productRules = pricelist.getRulesByProductId(product.id);
            rule = pricelist.findBestRule(productRules, quantity);
        }

        // 2. Template Rules
        if (!rule) {
            const tmplRules = pricelist.getRulesByTmplId(productTmpl.id);
            rule = pricelist.findBestRule(tmplRules, quantity);
        }

        // 3. Category Rules
        if (!rule) {
            const categoryRulesIds = pricelist.getCategoryRulesIds(this.parentCategories);
            if (categoryRulesIds.length > 0) {
                const categoryRules =
                    this.models["product.pricelist.item"].readMany(categoryRulesIds);
                rule = pricelist.findBestRule(categoryRules, quantity);
            }
        }

        // 4. Global Rules
        if (!rule) {
            const globalRulesIds = pricelist.getGlobalRulesIds();
            if (globalRulesIds.length > 0) {
                const globalRules = this.models["product.pricelist.item"].readMany(globalRulesIds);
                rule = pricelist.findBestRule(globalRules, quantity);
            }
        }

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

        const posCurrency = this.config.currency_id;
        const pricelistCurrency = pricelist.currency_id;
        const needsCurrencyConversion =
            pricelistCurrency && posCurrency && pricelistCurrency.id !== posCurrency.id;

        if (needsCurrencyConversion) {
            price *= pricelistCurrency.rate / posCurrency.rate;
        }

        if (rule.compute_price === "fixed") {
            price = rule.fixed_price;
        } else if (rule.compute_price === "percentage") {
            price = price - price * ((rule.percent_price || 0) / 100);
        } else {
            var price_limit = price;
            price -= price * ((rule.price_discount || 0) / 100);
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

        if (needsCurrencyConversion) {
            price *= posCurrency.rate / pricelistCurrency.rate;
        }

        // This return value has to be rounded with round_di before
        // being used further. Note that this cannot happen here,
        // because it would cause inconsistencies with the backend for
        // pricelist that have base == 'pricelist'.
        return price;
    }

    getBaseLine(opts = {}) {
        const vals = opts.overridedValues || {};
        const { price = false, pricelist = false, fiscalPosition = false, priceExtra = 0 } = vals;

        return accountTaxHelpers.prepare_base_line_for_taxes_computation(
            {},
            this.prepareProductBaseLineForTaxesComputationExtraValues({
                price,
                pricelist,
                fiscalPosition,
                priceExtra,
                ...vals,
            })
        );
    }

    getTaxDetails(opts = {}) {
        const config = this.config;
        const baseLine = this.getBaseLine(opts);
        accountTaxHelpers.add_tax_details_in_base_line(baseLine, config.company_id);
        accountTaxHelpers.round_base_lines_tax_details([baseLine], config.company_id);
        return baseLine.tax_details;
    }

    get displayPriceUnit() {
        const config = this.config;
        const price =
            config.iface_tax_included === "total"
                ? this.getTaxDetails().total_included
                : this.getTaxDetails().total_excluded;
        return formatCurrency(price, config.currency_id.id);
    }

    getComboTaxDetails(opts = {}) {
        const choices = [];
        const extraChoices = [];
        for (const combo of this.combo_ids) {
            let cheaps;
            const items = combo.combo_item_ids;

            if (combo.qty_free === 0) {
                cheaps = [...items].sort((a, b) => a.product_id.lst_price - b.product_id.lst_price);
            } else {
                cheaps = [...items].sort((a, b) => a.extra_price - b.extra_price);
            }

            const item = cheaps[0];
            let configuration = undefined;

            if (item.product_id.isConfigurable()) {
                const attrValIds = [];
                let priceExtra = 0;
                for (const attr of item.product_id.attribute_line_ids) {
                    const attrVals = attr.product_template_value_ids;
                    const sortedByCheaper = [...attrVals].sort(
                        (a, b) => a.price_extra - b.price_extra
                    );
                    attrValIds.push(sortedByCheaper[0].id);
                    priceExtra += sortedByCheaper[0].price_extra;
                }

                configuration = {
                    attribute_custom_values: [],
                    attribute_value_ids: attrValIds,
                    price_extra: priceExtra,
                };
            }

            const data = {
                combo_item_id: item,
                qty: combo.qty_free || 1,
                configuration: configuration,
            };

            if (combo.qty_free === 0) {
                extraChoices.push(data);
            } else {
                choices.push(data);
            }
        }

        const combos = this.getComboPrice(
            choices,
            extraChoices,
            opts.overridedValues?.pricelist || false
        );
        const overridedValues = opts.overridedValues || {};
        const baseLines = combos.map((combo) =>
            combo.combo_item_id.product_id.getBaseLine({
                ...opts,
                overridedValues: {
                    product_id: combo.combo_item_id.product_id,
                    quantity: combo.qty,
                    price: combo.price_unit,
                    ...overridedValues,
                },
            })
        );
        accountTaxHelpers.add_tax_details_in_base_lines(baseLines, this.config.company_id);
        accountTaxHelpers.round_base_lines_tax_details(baseLines, this.config.company_id);

        let taxDetails = baseLines.length > 0 ? baseLines[0].tax_details : null;
        for (let i = 1; i < baseLines.length; i++) {
            taxDetails = accountTaxHelpers.merge_tax_details(taxDetails, baseLines[i].tax_details);
        }
        return taxDetails;
    }

    getComboPrice(childLineConf = [], childLineExtra = [], pricelist = false) {
        const comboItems = [];
        const productTemplateAttributeValueById =
            this.models["product.template.attribute.value"].getAllBy("id");
        const decimalPrecision = this.models["decimal.precision"].getAll();
        const parentLstPrice = this.getPrice(pricelist, 1, 0, false, this);
        let originalTotal = childLineConf.reduce((acc, conf) => {
            const originalPrice = conf.combo_item_id.combo_id.base_price * conf.qty;
            return acc + originalPrice;
        }, 0);

        const getAttributesPriceExtra = (attributeValueIds) =>
            (attributeValueIds ?? [])
                .filter((attr) => attr?.attribute_id?.create_variant !== "always")
                .map((attr) => attr?.price_extra || 0)
                .reduce((acc, price) => acc + price, 0);

        let remainingTotal = parentLstPrice;
        const ProductPrice =
            this.config.currency_id || decimalPrecision.find((dp) => dp.name === "Product Price");
        if (childLineConf[childLineConf.length - 1]?.qty > 1) {
            childLineConf[childLineConf.length - 1].qty -= 1;
            childLineConf.push({ ...childLineConf[childLineConf.length - 1], qty: 1 });
        }
        for (const conf of childLineConf) {
            const comboItem = conf.combo_item_id;
            const combo = comboItem.combo_id;
            let priceUnit = ProductPrice.round((combo.base_price * parentLstPrice) / originalTotal);
            remainingTotal -= priceUnit * conf.qty;
            if (conf === childLineConf[childLineConf.length - 1]) {
                priceUnit += remainingTotal;
                remainingTotal = 0;
            }
            const attribute_value_ids = conf.configuration?.attribute_value_ids?.map(
                (id) => productTemplateAttributeValueById[id]
            );

            const totalPriceExtra =
                priceUnit + getAttributesPriceExtra(attribute_value_ids) + comboItem.extra_price;
            comboItems.push({
                combo_item_id: comboItem,
                price_unit: totalPriceExtra,
                attribute_value_ids:
                    attribute_value_ids ||
                    comboItem.product_id?.product_template_attribute_value_ids,
                attribute_custom_values: conf.configuration?.attribute_custom_values || {},
                qty: conf.qty,
            });
        }

        if (remainingTotal !== 0) {
            originalTotal = childLineExtra.reduce((acc, conf) => {
                const originalPrice = conf.combo_item_id.combo_id.base_price * conf.qty;
                return acc + originalPrice;
            }, 0);
        }

        // Process extra child lines using combo 'base_price'
        for (const extra of childLineExtra) {
            const comboItem = extra.combo_item_id;
            const combo = comboItem.combo_id;
            let priceUnit = ProductPrice.round(combo.base_price);
            if (remainingTotal !== 0) {
                const remaining = ProductPrice.round(
                    (combo.base_price * parentLstPrice) / originalTotal
                );
                priceUnit += remaining;
                remainingTotal -= remaining * extra.qty;

                if (comboItem.id == childLineExtra[childLineExtra.length - 1].combo_item_id.id) {
                    priceUnit += remainingTotal / extra.qty;
                }
            }
            const attribute_value_ids = extra.configuration?.attribute_value_ids.map(
                (id) => productTemplateAttributeValueById[id]
            );

            const totalPriceExtra =
                priceUnit + getAttributesPriceExtra(attribute_value_ids) + comboItem.extra_price;
            comboItems.push({
                combo_item_id: comboItem,
                price_unit: totalPriceExtra,
                attribute_value_ids:
                    attribute_value_ids ||
                    comboItem.product_id?.product_template_attribute_value_ids,
                attribute_custom_values: extra.configuration?.attribute_custom_values || {},
                qty: extra.qty,
            });
        }

        let sequenceCounter = 0;
        const mapSequence = this.combo_ids.reduce((acc, combo) => {
            combo.combo_item_ids.forEach((item) => {
                acc[item.id] = sequenceCounter++;
            });
            return acc;
        }, {});

        comboItems.sort(
            (a, b) =>
                (mapSequence[a.combo_item_id.id] ?? Infinity) -
                (mapSequence[b.combo_item_id.id] ?? Infinity)
        );
        return comboItems;
    }
}
