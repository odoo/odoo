/** @odoo-module */

import { formatMonetary } from "@web/views/fields/formatters";
import {
    formatFloat,
    roundDecimals,
    roundPrecision,
    floatIsZero as genericFloatIsZero,
} from "@web/core/utils/numbers";
import { escapeRegExp } from "@web/core/utils/strings";
import { registry } from "@web/core/registry";
import { parseFloat } from "@web/views/fields/parsers";

/* Returns an array containing all elements of the given
 * array corresponding to the rule function {agg} and without duplicates
 *
 * @template T
 * @template F
 * @param {T[]} array
 * @param {F} function
 * @returns {T[]}
 */
export function uniqueBy(array, agg) {
    const map = new Map();
    for (const item of array) {
        const key = agg(item);
        if (!map.has(key)) {
            map.set(key, item);
        }
    }
    return [...map.values()];
}

/**
 * This service introduces `utils` namespace in the `env` which can contain
 * functions that are parameterized by the data in `pos` service.
 */
export const contextualUtilsService = {
    dependencies: ["pos_data", "localization"],
    start(env, { pos_data, localization }) {
        const cache = {
            company: pos_data["res.company"],
            currency: pos_data["res.currency"],
            pricelists: pos_data["product.pricelist"],
            uom_unit_id: pos_data["uom_unit_id"],
            config: pos_data["pos.config"],
            base_url: pos_data["base_url"],
            dp: pos_data["decimal.precision"],
            picking_type: pos_data["stock.picking.type"],
            default_pricelist: pos_data["default_pricelist"],
            taxes_by_id: pos_data["taxes_by_id"],
            units_by_id: pos_data["units_by_id"],
            pos_session: pos_data["pos.session"],
            fiscal_positions: pos_data["account.fiscal.position"],
            user: pos_data["res.users"],
        };

        const productUoMDecimals = cache.dp["Product Unit of Measure"];
        const decimalPoint = localization.decimalPoint;
        const thousandsSep = localization.thousandsSep;
        // Replace the thousands separator and decimal point with regex-escaped versions
        const escapedDecimalPoint = escapeRegExp(decimalPoint);
        let floatRegex;
        if (thousandsSep) {
            const escapedThousandsSep = escapeRegExp(thousandsSep);
            floatRegex = new RegExp(
                `^-?(?:\\d+(${escapedThousandsSep}\\d+)*)?(?:${escapedDecimalPoint}\\d*)?$`
            );
        } else {
            floatRegex = new RegExp(`^-?(?:\\d+)?(?:${escapedDecimalPoint}\\d*)?$`);
        }

        const formatProductQty = (qty) => {
            return formatFloat(qty, { digits: [true, productUoMDecimals] });
        };

        const formatStrCurrency = (valueStr, hasSymbol = true) => {
            return formatCurrency(parseFloat(valueStr), hasSymbol);
        };

        const formatCurrency = (value, hasSymbol = true) => {
            return formatMonetary(value, {
                currencyId: cache.currency.id,
                noSymbol: !hasSymbol,
            });
        };
        const floatIsZero = (value) => {
            return genericFloatIsZero(value, cache.currency.decimal_places);
        };

        const roundCurrency = (value) => {
            return roundDecimals(value, cache.currency.decimal_places);
        };

        const isValidFloat = (inputValue) => {
            return ![decimalPoint, "-"].includes(inputValue) && floatRegex.test(inputValue);
        };

        /**
         * Mirror JS method of:
         * _compute_amount in addons/account/models/account.py
         */
        function _compute_amount(tax, base_amount, quantity, price_exclude) {
            if (price_exclude === undefined) {
                var price_include = tax.price_include;
            } else {
                price_include = !price_exclude;
            }
            if (tax.amount_type === "fixed") {
                // Use sign on base_amount and abs on quantity to take into account the sign of the base amount,
                // which includes the sign of the quantity and the sign of the price_unit
                // Amount is the fixed price for the tax, it can be negative
                // Base amount included the sign of the quantity and the sign of the unit price and when
                // a product is returned, it can be done either by changing the sign of quantity or by changing the
                // sign of the price unit.
                // When the price unit is equal to 0, the sign of the quantity is absorbed in base_amount then
                // a "else" case is needed.
                if (base_amount) {
                    return Math.sign(base_amount) * Math.abs(quantity) * tax.amount;
                } else {
                    return quantity * tax.amount;
                }
            }
            if (tax.amount_type === "percent" && !price_include) {
                return (base_amount * tax.amount) / 100;
            }
            if (tax.amount_type === "percent" && price_include) {
                return base_amount - base_amount / (1 + tax.amount / 100);
            }
            if (tax.amount_type === "division" && !price_include) {
                return base_amount / (1 - tax.amount / 100) - base_amount;
            }
            if (tax.amount_type === "division" && price_include) {
                return base_amount - base_amount * (tax.amount / 100);
            }
            return false;
        }

        /**
         * Mirror JS method of:
         * compute_all in addons/account/models/account.py
         *
         * Read comments in the python side method for more details about each sub-methods.
         */
        function compute_all(
            taxes,
            price_unit,
            quantity,
            currency_rounding,
            handle_price_include = true
        ) {
            // 1) Flatten the taxes.

            var _collect_taxes = function (taxes, all_taxes) {
                taxes = [...taxes].sort(function (tax1, tax2) {
                    return tax1.sequence - tax2.sequence;
                });
                taxes.forEach((tax) => {
                    if (tax.amount_type === "group") {
                        all_taxes = _collect_taxes(tax.children_tax_ids, all_taxes);
                    } else {
                        all_taxes.push(tax);
                    }
                });
                return all_taxes;
            };
            var collect_taxes = function (taxes) {
                return _collect_taxes(taxes, []);
            };

            taxes = collect_taxes(taxes);

            // 2) Deal with the rounding methods

            var round_tax = cache.company.tax_calculation_rounding_method != "round_globally";

            var initial_currency_rounding = currency_rounding;
            if (!round_tax) {
                currency_rounding = currency_rounding * 0.00001;
            }

            // 3) Iterate the taxes in the reversed sequence order to retrieve the initial base of the computation.
            var recompute_base = function (
                base_amount,
                fixed_amount,
                percent_amount,
                division_amount
            ) {
                return (
                    (((base_amount - fixed_amount) / (1.0 + percent_amount / 100.0)) *
                        (100 - division_amount)) /
                    100
                );
            };

            var base = roundPrecision(price_unit * quantity, initial_currency_rounding);

            var sign = 1;
            if (base < 0) {
                base = -base;
                sign = -1;
            }

            var total_included_checkpoints = {};
            var i = taxes.length - 1;
            var store_included_tax_total = true;

            var incl_fixed_amount = 0.0;
            var incl_percent_amount = 0.0;
            var incl_division_amount = 0.0;

            var cached_tax_amounts = {};
            if (handle_price_include) {
                taxes.reverse().forEach(function (tax) {
                    if (tax.include_base_amount) {
                        base = recompute_base(
                            base,
                            incl_fixed_amount,
                            incl_percent_amount,
                            incl_division_amount
                        );
                        incl_fixed_amount = 0.0;
                        incl_percent_amount = 0.0;
                        incl_division_amount = 0.0;
                        store_included_tax_total = true;
                    }
                    if (tax.price_include) {
                        if (tax.amount_type === "percent") {
                            incl_percent_amount += tax.amount * tax.sum_repartition_factor;
                        } else if (tax.amount_type === "division") {
                            incl_division_amount += tax.amount * tax.sum_repartition_factor;
                        } else if (tax.amount_type === "fixed") {
                            incl_fixed_amount +=
                                Math.abs(quantity) * tax.amount * tax.sum_repartition_factor;
                        } else {
                            var tax_amount = _compute_amount(tax, base, quantity);
                            incl_fixed_amount += tax_amount;
                            cached_tax_amounts[i] = tax_amount;
                        }
                        if (store_included_tax_total) {
                            total_included_checkpoints[i] = base;
                            store_included_tax_total = false;
                        }
                    }
                    i -= 1;
                });
            }

            var total_excluded = roundPrecision(
                recompute_base(base, incl_fixed_amount, incl_percent_amount, incl_division_amount),
                initial_currency_rounding
            );
            var total_included = total_excluded;

            // 4) Iterate the taxes in the sequence order to fill missing base/amount values.

            base = total_excluded;

            var skip_checkpoint = false;

            var taxes_vals = [];
            i = 0;
            var cumulated_tax_included_amount = 0;
            taxes.reverse().forEach(function (tax) {
                if (tax.price_include || tax.is_base_affected) {
                    var tax_base_amount = base;
                } else {
                    tax_base_amount = total_excluded;
                }

                if (
                    !skip_checkpoint &&
                    tax.price_include &&
                    total_included_checkpoints[i] !== undefined &&
                    tax.sum_repartition_factor != 0
                ) {
                    var tax_amount =
                        total_included_checkpoints[i] - (base + cumulated_tax_included_amount);
                    cumulated_tax_included_amount = 0;
                } else {
                    tax_amount = _compute_amount(tax, tax_base_amount, quantity, true);
                }

                tax_amount = roundPrecision(tax_amount, currency_rounding);
                var factorized_tax_amount = roundPrecision(
                    tax_amount * tax.sum_repartition_factor,
                    currency_rounding
                );

                if (tax.price_include && total_included_checkpoints[i] === undefined) {
                    cumulated_tax_included_amount += factorized_tax_amount;
                }

                taxes_vals.push({
                    id: tax.id,
                    name: tax.name,
                    amount: sign * factorized_tax_amount,
                    base: sign * roundPrecision(tax_base_amount, currency_rounding),
                });

                if (tax.include_base_amount) {
                    base += factorized_tax_amount;
                    if (!tax.price_include) {
                        skip_checkpoint = true;
                    }
                }

                total_included += factorized_tax_amount;
                i += 1;
            });

            return {
                taxes: taxes_vals,
                total_excluded: sign * roundPrecision(total_excluded, cache.currency.rounding),
                total_included: sign * roundPrecision(total_included, cache.currency.rounding),
            };
        }

        /**
         * Taxes after fiscal position mapping.
         * @param {number[]} taxIds
         * @param {object | falsy} fpos - fiscal position
         * @returns {object[]}
         */
        function get_taxes_after_fp(taxIds, fpos) {
            if (!fpos) {
                return taxIds.map((taxId) => cache.taxes_by_id[taxId]);
            }
            const mappedTaxes = [];
            for (const taxId of taxIds) {
                const tax = cache.taxes_by_id[taxId];
                if (tax) {
                    const taxMaps = Object.values(fpos.fiscal_position_taxes_by_id).filter(
                        (fposTax) => fposTax.tax_src_id[0] === tax.id
                    );
                    if (taxMaps.length) {
                        for (const taxMap of taxMaps) {
                            if (taxMap.tax_dest_id) {
                                const mappedTax = cache.taxes_by_id[taxMap.tax_dest_id[0]];
                                if (mappedTax) {
                                    mappedTaxes.push(mappedTax);
                                }
                            }
                        }
                    } else {
                        mappedTaxes.push(tax);
                    }
                }
            }
            return uniqueBy(mappedTaxes, (tax) => tax.id);
        }

        function computePriceAfterFp(price, taxes, fiscal_position) {
            if (fiscal_position) {
                const mapped_included_taxes = [];
                let new_included_taxes = [];
                taxes.forEach((tax) => {
                    const line_taxes = get_taxes_after_fp([tax.id], fiscal_position);
                    if (line_taxes.length && line_taxes[0].price_include) {
                        new_included_taxes = new_included_taxes.concat(line_taxes);
                    }
                    if (tax.price_include && !line_taxes.includes(tax)) {
                        mapped_included_taxes.push(tax);
                    }
                });

                if (mapped_included_taxes.length > 0) {
                    if (new_included_taxes.length > 0) {
                        const price_without_taxes = compute_all(
                            mapped_included_taxes,
                            price,
                            1,
                            cache.currency.rounding,
                            true
                        ).total_excluded;
                        return compute_all(
                            new_included_taxes,
                            price_without_taxes,
                            1,
                            cache.currency.rounding,
                            false
                        ).total_included;
                    } else {
                        return compute_all(
                            mapped_included_taxes,
                            price,
                            1,
                            cache.currency.rounding,
                            true
                        ).total_excluded;
                    }
                }
            }
            return price;
        }

        function getTaxesByIds(taxIds) {
            const taxes = [];
            for (let i = 0; i < taxIds.length; i++) {
                if (cache.taxes_by_id[taxIds[i]]) {
                    taxes.push(cache.taxes_by_id[taxIds[i]]);
                }
            }
            return taxes;
        }
        function _assignApplicableItems(pricelist, correspondingProduct, pricelistItem) {
            if (!(pricelist.id in correspondingProduct.applicablePricelistItems)) {
                correspondingProduct.applicablePricelistItems[pricelist.id] = [];
            }
            correspondingProduct.applicablePricelistItems[pricelist.id].push(pricelistItem);
        }
        function initializeProducts(products, productClass, params = {}) {
            const productMap = {};
            const productTemplateMap = {};

            const modelProducts = products.map((product) => {
                product.applicablePricelistItems = {};
                productMap[product.id] = product;
                productTemplateMap[product.product_tmpl_id[0]] = (
                    productTemplateMap[product.product_tmpl_id[0]] || []
                ).concat(product);
                return new productClass({ env, ...params }, product);
            });

            for (const pricelist of cache.pricelists) {
                for (const pricelistItem of pricelist.items) {
                    if (pricelistItem.product_id) {
                        const product_id = pricelistItem.product_id[0];
                        const correspondingProduct = productMap[product_id];
                        if (correspondingProduct) {
                            _assignApplicableItems(pricelist, correspondingProduct, pricelistItem);
                        }
                    } else if (pricelistItem.product_tmpl_id) {
                        const product_tmpl_id = pricelistItem.product_tmpl_id[0];
                        const correspondingProducts = productTemplateMap[product_tmpl_id];
                        for (const correspondingProduct of correspondingProducts || []) {
                            _assignApplicableItems(pricelist, correspondingProduct, pricelistItem);
                        }
                    } else {
                        for (const correspondingProduct of products) {
                            _assignApplicableItems(pricelist, correspondingProduct, pricelistItem);
                        }
                    }
                }
            }
            return modelProducts;
        }

        env.utils = {
            formatCurrency,
            formatStrCurrency,
            roundCurrency,
            formatProductQty,
            isValidFloat,
            floatIsZero,
            compute_all,
            computePriceAfterFp,
            get_taxes_after_fp,
            getTaxesByIds,
            initializeProducts,
        };
        env.cache = cache;
    },
};

registry.category("services").add("contextual_utils_service", contextualUtilsService);
