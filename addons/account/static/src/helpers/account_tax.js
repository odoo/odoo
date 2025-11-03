import { floatIsZero, roundPrecision } from "@web/core/utils/numbers";
import { _t } from "@web/core/l10n/translation";

export const accountTaxHelpers = {
    // -------------------------------------------------------------------------
    // HELPERS IN BOTH PYTHON/JAVASCRIPT (account_tax.js / account_tax.py)
    // -------------------------------------------------------------------------

    /**
     * Helper to stringify a grouping key that could contains some records.
     *
     * [!] Only added javascript-side.
     */
    stringify_grouping_key(grouping_key) {
        if (!grouping_key || typeof grouping_key !== "object") {
            return grouping_key;
        }

        if ("id" in grouping_key) {
            return grouping_key.id;
        }

        const serializable_grouping_key = { ...grouping_key };
        for (const [key, value] of Object.entries(grouping_key)) {
            if (value && typeof value === "object" && "id" in value) {
                serializable_grouping_key[key] = value.id;
            }
        }
        return JSON.stringify(serializable_grouping_key);
    },

    // -------------------------------------------------------------------------
    // PREPARE TAXES COMPUTATION
    // -------------------------------------------------------------------------

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    flatten_taxes_and_sort_them(taxes) {
        function sort_key(taxes) {
            return taxes.toSorted((t1, t2) => t1.sequence - t2.sequence || t1.id - t2.id);
        }

        const group_per_tax = {};
        const sorted_taxes = [];
        for (const tax of sort_key(taxes)) {
            if (tax.amount_type === "group") {
                const children = sort_key(tax.children_tax_ids);
                for (const child of children) {
                    group_per_tax[child.id] = tax;
                    sorted_taxes.push(child);
                }
            } else {
                sorted_taxes.push(tax);
            }
        }
        return { sorted_taxes, group_per_tax };
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    batch_for_taxes_computation(taxes, { special_mode = null, filter_tax_function = null } = {}) {
        let { sorted_taxes, group_per_tax } = this.flatten_taxes_and_sort_them(taxes);
        if (filter_tax_function) {
            sorted_taxes = sorted_taxes.filter(filter_tax_function);
        }

        const results = {
            batch_per_tax: {},
            group_per_tax: group_per_tax,
            sorted_taxes: sorted_taxes,
        };

        // Group them per batch.
        let batch = [];
        let is_base_affected = false;
        for (const tax of results.sorted_taxes.toReversed()) {
            if (batch.length > 0) {
                const same_batch =
                    tax.amount_type === batch[0].amount_type &&
                    (special_mode || tax.price_include === batch[0].price_include) &&
                    tax.include_base_amount === batch[0].include_base_amount &&
                    ((tax.include_base_amount && !is_base_affected) || !tax.include_base_amount);
                if (!same_batch) {
                    for (const batch_tax of batch) {
                        results.batch_per_tax[batch_tax.id] = batch;
                    }
                    batch = [];
                }
            }

            is_base_affected = tax.is_base_affected;
            batch.push(tax);
        }

        if (batch.length !== 0) {
            for (const batch_tax of batch) {
                results.batch_per_tax[batch_tax.id] = batch;
            }
        }
        return results;
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    propagate_extra_taxes_base(taxes, tax, taxes_data, { special_mode = null } = {}) {
        function* get_tax_before() {
            for (const tax_before of taxes) {
                if (taxes_data[tax.id].batch.includes(tax_before)) {
                    break;
                }
                yield tax_before;
            }
        }

        function* get_tax_after() {
            for (const tax_after of taxes.toReversed()) {
                if (taxes_data[tax.id].batch.includes(tax_after)) {
                    break;
                }
                yield tax_after;
            }
        }

        function add_extra_base(other_tax, sign) {
            const tax_amount = taxes_data[tax.id].tax_amount;
            if (!("tax_amount" in taxes_data[other_tax.id])) {
                taxes_data[other_tax.id].extra_base_for_tax += sign * tax_amount;
            }
            taxes_data[other_tax.id].extra_base_for_base += sign * tax_amount;
        }

        if (tax.price_include) {
            // Case: special mode is False or 'total_included'
            if (!special_mode || special_mode === "total_included") {
                if (tax.include_base_amount) {
                    for (const other_tax of get_tax_after()) {
                        if (!other_tax.is_base_affected) {
                            add_extra_base(other_tax, -1);
                        }
                    }
                } else {
                    for (const other_tax of get_tax_after()) {
                        add_extra_base(other_tax, -1);
                    }
                }
                for (const other_tax of get_tax_before()) {
                    add_extra_base(other_tax, -1);
                }

                // Case: special_mode = 'total_excluded'
            } else {
                if (tax.include_base_amount) {
                    for (const other_tax of get_tax_after()) {
                        if (other_tax.is_base_affected) {
                            add_extra_base(other_tax, 1);
                        }
                    }
                }
            }
        } else if (!tax.price_include) {
            // Case: special_mode is False or 'total_excluded'
            if (!special_mode || special_mode === "total_excluded") {
                if (tax.include_base_amount) {
                    for (const other_tax of get_tax_after()) {
                        if (other_tax.is_base_affected) {
                            add_extra_base(other_tax, 1);
                        }
                    }
                }

                // Case: special_mode = 'total_included'
            } else {
                if (!tax.include_base_amount) {
                    for (const other_tax of get_tax_after()) {
                        add_extra_base(other_tax, -1);
                    }
                }
                for (const other_tax of get_tax_before()) {
                    add_extra_base(other_tax, -1);
                }
            }
        }
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    eval_tax_amount_fixed_amount(tax, batch, raw_base, evaluation_context) {
        if (tax.amount_type === "fixed") {
            const sign = evaluation_context.price_unit < 0.0 ? -1 : 1;
            return sign * evaluation_context.quantity * tax.amount;
        }
        return null;
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    eval_tax_amount_price_included(tax, batch, raw_base, evaluation_context) {
        if (tax.amount_type === "percent") {
            const total_percentage =
                batch.reduce((sum, batch_tax) => sum + batch_tax.amount, 0) / 100.0;
            const to_price_excluded_factor =
                total_percentage !== -1 ? 1 / (1 + total_percentage) : 0.0;
            return (raw_base * to_price_excluded_factor * tax.amount) / 100.0;
        }

        if (tax.amount_type === "division") {
            return (raw_base * tax.amount) / 100.0;
        }
        return null;
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    eval_tax_amount_price_excluded(tax, batch, raw_base, evaluation_context) {
        if (tax.amount_type === "percent") {
            return (raw_base * tax.amount) / 100.0;
        }

        if (tax.amount_type === "division") {
            const total_percentage =
                batch.reduce((sum, batch_tax) => sum + batch_tax.amount, 0) / 100.0;
            const incl_base_multiplicator = total_percentage === 1.0 ? 1.0 : 1 - total_percentage;
            return (raw_base * tax.amount) / 100.0 / incl_base_multiplicator;
        }
        return null;
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    get_tax_details(
        taxes,
        price_unit,
        quantity,
        {
            precision_rounding = null,
            rounding_method = "round_per_line",
            // When product is null, we need the product default values to make the "formula" taxes
            // working. In that case, we need to deal with the product default values before calling this
            // method because we have no way to deal with it automatically in this method since it depends of
            // the type of involved fields and we don't have access to this information js-side.
            product = null,
            special_mode = null,
            manual_tax_amounts = null, // TO BE REMOVED IN MASTER
            filter_tax_function = null,
        } = {}
    ) {
        const self = this;

        function add_tax_amount_to_results(tax, tax_amount) {
            taxes_data[tax.id].tax_amount = tax_amount;
            if (rounding_method === "round_per_line") {
                taxes_data[tax.id].tax_amount = roundPrecision(
                    taxes_data[tax.id].tax_amount,
                    precision_rounding
                );
            }
            if (tax.has_negative_factor) {
                reverse_charge_taxes_data[tax.id].tax_amount = -taxes_data[tax.id].tax_amount;
            }

            self.propagate_extra_taxes_base(sorted_taxes, tax, taxes_data, {
                special_mode: special_mode,
            });
        }

        function eval_tax_amount(tax_amount_function, tax) {
            const is_already_computed = "tax_amount" in taxes_data[tax.id];
            if (is_already_computed) {
                return;
            }

            const tax_amount = tax_amount_function(
                tax,
                taxes_data[tax.id].batch,
                raw_base + taxes_data[tax.id].extra_base_for_tax,
                evaluation_context
            );
            if (tax_amount !== null) {
                add_tax_amount_to_results(tax, tax_amount);
            }
        }

        // Flatten the taxes, order them and filter them if necessary.

        function prepare_tax_extra_data(tax, kwargs = {}) {
            let price_include;
            if (tax.has_negative_factor) {
                price_include = false;
            } else if (special_mode === "total_included") {
                price_include = true;
            } else if (special_mode === "total_excluded") {
                price_include = false;
            } else {
                price_include = tax.price_include;
            }
            return {
                ...kwargs,
                tax: tax,
                price_include: price_include,
                extra_base_for_tax: 0.0,
                extra_base_for_base: 0.0,
            };
        }

        const batching_results = this.batch_for_taxes_computation(taxes, {
            special_mode: special_mode,
            filter_tax_function: filter_tax_function,
        });
        let sorted_taxes = batching_results.sorted_taxes;
        const taxes_data = {};
        const reverse_charge_taxes_data = {};
        for (const tax of sorted_taxes) {
            taxes_data[tax.id] = prepare_tax_extra_data(tax, {
                group: batching_results.group_per_tax[tax.id],
                batch: batching_results.batch_per_tax[tax.id],
            });
            if (tax.has_negative_factor) {
                reverse_charge_taxes_data[tax.id] = {
                    ...taxes_data[tax.id],
                    is_reverse_charge: true,
                };
            }
        }

        let raw_base = quantity * price_unit;
        if (rounding_method === "round_per_line") {
            raw_base = roundPrecision(raw_base, precision_rounding);
        }

        let evaluation_context = {
            product: product || {},
            price_unit: price_unit,
            quantity: quantity,
            raw_base: raw_base,
            special_mode: special_mode,
        };

        // Define the order in which the taxes must be evaluated.
        // Fixed taxes are computed directly because they could affect the base of a price included batch right after.
        for (const tax of sorted_taxes.toReversed()) {
            eval_tax_amount(this.eval_tax_amount_fixed_amount.bind(this), tax);
        }

        // Then, let's travel the batches in the reverse order and process the price-included taxes.
        for (const tax of sorted_taxes.toReversed()) {
            if (taxes_data[tax.id].price_include) {
                eval_tax_amount(this.eval_tax_amount_price_included.bind(this), tax);
            }
        }

        // Then, let's travel the batches in the normal order and process the price-excluded taxes.
        for (const tax of sorted_taxes) {
            if (!taxes_data[tax.id].price_include) {
                eval_tax_amount(this.eval_tax_amount_price_excluded.bind(this), tax);
            }
        }

        // Mark the base to be computed in the descending order. The order doesn't matter for no special mode or 'total_excluded' but
        // it must be in the reverse order when special_mode is 'total_included'.
        const subsequent_taxes = [];
        for (const tax of sorted_taxes.toReversed()) {
            const tax_data = taxes_data[tax.id];
            if (!("tax_amount" in tax_data)) {
                continue;
            }

            // Base amount.
            const total_tax_amount =
                taxes_data[tax.id].batch.reduce(
                    (sum, other_tax) => sum + taxes_data[other_tax.id].tax_amount,
                    0
                ) +
                Object.values(taxes_data[tax.id].batch)
                    .filter((other_tax) => other_tax.has_negative_factor)
                    .reduce(
                        (sum, other_tax) =>
                            sum + reverse_charge_taxes_data[other_tax.id].tax_amount,
                        0
                    );
            let base = raw_base + taxes_data[tax.id].extra_base_for_base;
            if (tax_data.price_include && (!special_mode || special_mode === "total_included")) {
                base -= total_tax_amount;
            }
            tax_data.base = base;

            // Subsequence taxes.
            tax_data.taxes = [];
            if (tax.include_base_amount) {
                tax_data.taxes.push(...subsequent_taxes);
            }

            // Reverse charge.
            if (tax.has_negative_factor) {
                const reverse_charge_tax_data = reverse_charge_taxes_data[tax.id];
                reverse_charge_tax_data.base = base;
                reverse_charge_tax_data.taxes = tax_data.taxes;
            }

            if (tax.is_base_affected) {
                subsequent_taxes.push(tax);
            }
        }

        const taxes_data_list = [];
        for (const tax of sorted_taxes) {
            const tax_data = taxes_data[tax.id];
            if ("tax_amount" in tax_data) {
                taxes_data_list.push(tax_data);
                if (tax.has_negative_factor) {
                    taxes_data_list.push(reverse_charge_taxes_data[tax.id]);
                }
            }
        }

        let total_excluded, total_included;
        if (taxes_data_list.length > 0) {
            total_excluded = taxes_data_list[0].base;
            const tax_amount = taxes_data_list.reduce(
                (sum, tax_data) => sum + tax_data.tax_amount,
                0
            );
            total_included = total_excluded + tax_amount;
        } else {
            total_excluded = total_included = raw_base;
        }

        return {
            total_excluded: total_excluded,
            total_included: total_included,
            taxes_data: taxes_data_list.map((tax_data) =>
                Object.assign(
                    {},
                    {
                        tax: tax_data.tax,
                        taxes: tax_data.taxes,
                        group: batching_results.group_per_tax[tax_data.tax.id],
                        batch: batching_results.batch_per_tax[tax_data.tax.id],
                        tax_amount: tax_data.tax_amount,
                        price_include: tax_data.price_include,
                        base_amount: tax_data.base,
                        is_reverse_charge: tax_data.is_reverse_charge || false,
                    }
                )
            ),
        };
    },

    // -------------------------------------------------------------------------
    // MAPPING PRICE_UNIT
    // -------------------------------------------------------------------------

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    adapt_price_unit_to_another_taxes(price_unit, product, original_taxes, new_taxes) {
        const original_tax_ids = new Set(original_taxes.map((x) => x.id));
        const new_tax_ids = new Set(new_taxes.map((x) => x.id));
        if (
            (original_tax_ids.size === new_tax_ids.size &&
                [...original_tax_ids].every((value) => new_tax_ids.has(value))) ||
            original_taxes.some((x) => !x.price_include)
        ) {
            return price_unit;
        }

        // Find the price unit without tax.
        let taxes_computation = this.get_tax_details(original_taxes, price_unit, 1.0, {
            rounding_method: "round_globally",
            product: product,
        });
        price_unit = taxes_computation.total_excluded;

        // Find the new price unit after applying the price included taxes.
        taxes_computation = this.get_tax_details(new_taxes, price_unit, 1.0, {
            rounding_method: "round_globally",
            product: product,
            special_mode: "total_excluded",
        });
        let delta = 0.0;
        for (const tax_data of taxes_computation.taxes_data) {
            if (tax_data.tax.price_include) {
                delta += tax_data.tax_amount;
            }
        }
        return price_unit + delta;
    },

    // -------------------------------------------------------------------------
    // GENERIC REPRESENTATION OF BUSINESS OBJECTS & METHODS
    // -------------------------------------------------------------------------

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    export_base_line_extra_tax_data(base_line) {
        const results = {};
        if (base_line.computation_key) {
            results.computation_key = base_line.computation_key;
        }

        let store_source_data = false;
        if (base_line.manual_total_excluded_currency !== null) {
            results.manual_total_excluded_currency = base_line.manual_total_excluded_currency;
            store_source_data = true;
        }
        if (base_line.manual_total_excluded !== null) {
            results.manual_total_excluded = base_line.manual_total_excluded;
            store_source_data = true;
        }
        if (base_line.manual_tax_amounts && Object.keys(base_line.manual_tax_amounts).length > 0) {
            results.manual_tax_amounts = base_line.manual_tax_amounts;
            store_source_data = true;
        }

        if (store_source_data) {
            Object.assign(results, {
                currency_id: base_line.currency_id.id,
                price_unit: base_line.price_unit,
                discount: base_line.discount,
                quantity: base_line.quantity,
                rate: base_line.rate,
            });
        }
        return results;
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    import_base_line_extra_tax_data(base_line, extra_tax_data) {
        const currency_dp = base_line.currency_id.decimal_places;

        // compare_amounts does not exist in numbers.js
        const are_amounts_equal = (a, b) =>
            floatIsZero(
                roundPrecision(a, currency_dp) - roundPrecision(b, currency_dp),
                currency_dp
            );

        const results = {};

        if (extra_tax_data && extra_tax_data.computation_key) {
            results.computation_key = extra_tax_data.computation_key;
        }

        const manual_tax_amounts = extra_tax_data ? extra_tax_data.manual_tax_amounts || {} : null;
        const extra_tax_data_tax_ids = new Set(Object.keys(manual_tax_amounts || {}));
        const { sorted_taxes } = this.flatten_taxes_and_sort_them(base_line.tax_ids);
        if (
            extra_tax_data &&
            extra_tax_data.currency_id &&
            base_line.currency_id.id === extra_tax_data.currency_id &&
            are_amounts_equal(base_line.price_unit, extra_tax_data.price_unit) &&
            are_amounts_equal(base_line.discount, extra_tax_data.discount) &&
            are_amounts_equal(base_line.quantity, extra_tax_data.quantity) &&
            sorted_taxes.length === extra_tax_data_tax_ids.size &&
            sorted_taxes
                .map((tax) => tax.id.toString())
                .every((tax_id_str) => extra_tax_data_tax_ids.has(tax_id_str))
        ) {
            results.price_unit = extra_tax_data.price_unit;

            let delta_rate;
            if (base_line.rate && extra_tax_data.rate) {
                delta_rate = base_line.rate / extra_tax_data.rate;
            } else {
                delta_rate = 1.0;
            }

            if ("manual_total_excluded_currency" in extra_tax_data) {
                results.manual_total_excluded_currency =
                    extra_tax_data.manual_total_excluded_currency;
            }
            if ("manual_total_excluded" in extra_tax_data) {
                results.manual_total_excluded = extra_tax_data.manual_total_excluded / delta_rate;
            }

            if (manual_tax_amounts) {
                results.manual_tax_amounts = {};
                for (const [tax_id_str, amounts] of Object.entries(
                    extra_tax_data.manual_tax_amounts
                )) {
                    results.manual_tax_amounts[tax_id_str] = { ...amounts };
                    if ("tax_amount" in amounts) {
                        results.manual_tax_amounts[tax_id_str].tax_amount /= delta_rate;
                    }
                    if ("base_amount" in amounts) {
                        results.manual_tax_amounts[tax_id_str].base_amount /= delta_rate;
                    }
                }
            }
        }
        return results;
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    get_base_line_field_value_from_record(record, field, extra_values, fallback) {
        if (field in extra_values) {
            return extra_values[field] || fallback;
        }
        if (record && field in record) {
            return record[field] || fallback;
        }
        return fallback;
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    prepare_base_line_for_taxes_computation(record, kwargs = {}) {
        const load = (field, fallback) =>
            this.get_base_line_field_value_from_record(record, field, kwargs, fallback);
        const currency =
            load("currency_id", null) ||
            load("company_currency_id", null) ||
            load("company_id", {}).currency_id ||
            {};

        const base_line = {
            ...kwargs,
            record: record,
            id: load("id", 0),
            product_id: load("product_id", {}),
            product_uom_id: load("product_uom_id", {}),
            tax_ids: load("tax_ids", []),
            price_unit: load("price_unit", 0.0),
            quantity: load("quantity", 0.0),
            discount: load("discount", 0.0),
            currency_id: currency,
            sign: load("sign", 1.0),
            special_mode: kwargs.special_mode || null,
            special_type: kwargs.special_type || null,
            rate: load("rate", 1.0),
            filter_tax_function: kwargs.filter_tax_function || null,
        };

        const extra_tax_data = this.import_base_line_extra_tax_data(
            base_line,
            load("extra_tax_data", {}) || {}
        );
        Object.assign(base_line, {
            manual_total_excluded_currency:
                kwargs.manual_total_excluded_currency ||
                extra_tax_data.manual_total_excluded_currency ||
                null,
            manual_total_excluded:
                kwargs.manual_total_excluded || extra_tax_data.manual_total_excluded || null,
            computation_key: kwargs.computation_key || extra_tax_data.computation_key || null,
            manual_tax_amounts:
                kwargs.manual_tax_amounts || extra_tax_data.manual_tax_amounts || null,
        });
        if ("price_unit" in extra_tax_data) {
            base_line.price_unit = extra_tax_data.price_unit;
        }

        // Propagate custom values.
        if (record && typeof record === "object") {
            for (const [k, v] of Object.entries(record)) {
                if (k && typeof k === "string" && k.startsWith("_") && !(k in base_line)) {
                    base_line[k] = v;
                }
            }
        }

        return base_line;
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    add_tax_details_in_base_line(base_line, company, { rounding_method = null } = {}) {
        rounding_method = rounding_method || company.tax_calculation_rounding_method;
        const price_unit_after_discount = base_line.price_unit * (1 - base_line.discount / 100.0);
        const currency_pd = base_line.currency_id.rounding;
        const company_currency_pd = company.currency_id.rounding;
        const taxes_computation = this.get_tax_details(
            base_line.tax_ids,
            price_unit_after_discount,
            base_line.quantity,
            {
                precision_rounding: currency_pd,
                rounding_method: rounding_method,
                product: base_line.product_id,
                special_mode: base_line.special_mode,
                filter_tax_function: base_line.filter_tax_function,
            }
        );

        const rate = base_line.rate;
        const tax_details = (base_line.tax_details = {
            raw_total_excluded_currency: taxes_computation.total_excluded,
            raw_total_excluded: rate ? taxes_computation.total_excluded / rate : 0.0,
            raw_total_included_currency: taxes_computation.total_included,
            raw_total_included: rate ? taxes_computation.total_included / rate : 0.0,
            taxes_data: [],
        });

        if (rounding_method === "round_per_line") {
            tax_details.raw_total_excluded = roundPrecision(
                tax_details.raw_total_excluded,
                currency_pd
            );
            tax_details.raw_total_included = roundPrecision(
                tax_details.raw_total_included,
                currency_pd
            );
        }

        for (const tax_data of taxes_computation.taxes_data) {
            let tax_amount = rate ? tax_data.tax_amount / rate : 0.0;
            let base_amount = rate ? tax_data.base_amount / rate : 0.0;

            if (rounding_method === "round_per_line") {
                tax_amount = roundPrecision(tax_amount, company_currency_pd);
                base_amount = roundPrecision(base_amount, company_currency_pd);
            }

            tax_details.taxes_data.push({
                ...tax_data,
                raw_tax_amount_currency: tax_data.tax_amount,
                raw_tax_amount: tax_amount,
                raw_base_amount_currency: tax_data.base_amount,
                raw_base_amount: base_amount,
            });
        }
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    add_tax_details_in_base_lines(base_lines, company) {
        for (const base_line of base_lines) {
            this.add_tax_details_in_base_line(base_line, company);
        }
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    distribute_delta_amount_smoothly(precision_digits, delta_amount, target_factors) {
        const precision_rounding = Number(`1e-${precision_digits}`);
        const amounts_to_distribute = target_factors.map((x) => 0.0);
        if (floatIsZero(delta_amount, precision_digits)) {
            return amounts_to_distribute;
        }

        const sign = delta_amount < 0.0 ? -1 : 1;
        const nb_of_errors = Math.round(Math.abs(delta_amount / precision_rounding));
        let remaining_errors = nb_of_errors;

        // Take absolute value of factors and sort them by largest absolute value first
        const factors = target_factors.map((x, i) => [i, Math.abs(x.factor)]);
        factors.sort((a, b) => b[1] - a[1]);
        const sum_of_factors = factors.reduce((sum, x) => sum + x[1], 0.0);
        if (sum_of_factors === 0.0) {
            return amounts_to_distribute;
        }

        for (const [i, factor] of factors) {
            if (remaining_errors === 0) {
                break;
            }

            const nb_of_amount_to_distribute = Math.min(
                Math.ceil(Math.abs((factor / sum_of_factors) * nb_of_errors)),
                remaining_errors
            );

            remaining_errors -= nb_of_amount_to_distribute;
            const amount_to_distribute = sign * nb_of_amount_to_distribute * precision_rounding;
            amounts_to_distribute[i] += amount_to_distribute;
        }

        return amounts_to_distribute;
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    round_tax_details_tax_amounts(base_lines, company, { mode = "mixed" } = {}) {
        function grouping_function(base_line, tax_data) {
            if (!tax_data) {
                return;
            }
            return {
                is_refund: base_line.is_refund,
                is_reverse_charge: tax_data.is_reverse_charge,
                price_include: tax_data.price_include,
                computation_key: base_line.computation_key,
                tax: tax_data.tax,
                currency: base_line.currency_id,
            };
        }

        const base_lines_aggregated_values = this.aggregate_base_lines_tax_details(
            base_lines,
            grouping_function
        );
        const values_per_grouping_key = this.aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        );
        for (const values of Object.values(values_per_grouping_key)) {
            const grouping_key = values.grouping_key;
            if (!grouping_key) {
                continue;
            }

            const price_include = grouping_key.price_include;
            const currency = grouping_key.currency;
            for (const [delta_currency_indicator, delta_currency] of [
                ["_currency", currency],
                ["", company.currency_id],
            ]) {
                // Tax amount
                const raw_total_tax_amount = values[`target_tax_amount${delta_currency_indicator}`];
                const rounded_raw_total_tax_amount = roundPrecision(
                    raw_total_tax_amount,
                    delta_currency.rounding
                );
                const total_tax_amount = values[`tax_amount${delta_currency_indicator}`];
                const delta_total_tax_amount = rounded_raw_total_tax_amount - total_tax_amount;

                if (raw_total_tax_amount) {
                    const target_factors = values.base_line_x_taxes_data.flatMap(
                        ([_, taxes_data]) =>
                            taxes_data.map((tax_data) => ({
                                factor: tax_data[`raw_tax_amount${delta_currency_indicator}`],
                                tax_data: tax_data,
                            }))
                    );

                    const amounts_to_distribute = this.distribute_delta_amount_smoothly(
                        delta_currency.decimal_places,
                        delta_total_tax_amount,
                        target_factors
                    );

                    for (let i = 0; i < target_factors.length; i++) {
                        const tax_data = target_factors[i].tax_data;
                        const amount_to_distribute = amounts_to_distribute[i];
                        tax_data[`tax_amount${delta_currency_indicator}`] += amount_to_distribute;
                    }
                }

                // Base amount
                const raw_total_base_amount =
                    values[`target_base_amount${delta_currency_indicator}`];
                let delta_total_base_amount = 0.0;

                if ((mode === "mixed" && price_include) || mode === "included") {
                    const raw_total_amount = raw_total_base_amount + raw_total_tax_amount;
                    const rounded_raw_total_amount = roundPrecision(
                        raw_total_amount,
                        delta_currency.rounding
                    );
                    const total_amount =
                        values[`base_amount${delta_currency_indicator}`] +
                        total_tax_amount +
                        delta_total_tax_amount;
                    delta_total_base_amount = rounded_raw_total_amount - total_amount;
                } else if ((mode === "mixed" && !price_include) || mode === "excluded") {
                    const rounded_raw_total_base_amount = roundPrecision(
                        raw_total_base_amount,
                        delta_currency.rounding
                    );
                    const total_base_amount = values[`base_amount${delta_currency_indicator}`];
                    delta_total_base_amount = rounded_raw_total_base_amount - total_base_amount;
                }

                if (raw_total_base_amount) {
                    const target_factors = values.base_line_x_taxes_data.flatMap(
                        ([_, taxes_data]) =>
                            taxes_data.map((tax_data) => ({
                                factor: tax_data[`raw_base_amount${delta_currency_indicator}`],
                                tax_data: tax_data,
                            }))
                    );

                    const amounts_to_distribute = this.distribute_delta_amount_smoothly(
                        delta_currency.decimal_places,
                        delta_total_base_amount,
                        target_factors
                    );

                    for (let i = 0; i < target_factors.length; i++) {
                        const tax_data = target_factors[i].tax_data;
                        const amount_to_distribute = amounts_to_distribute[i];
                        tax_data[`base_amount${delta_currency_indicator}`] += amount_to_distribute;
                    }
                }
            }
        }
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    round_tax_details_base_lines(base_lines, company, { mode = "mixed" } = {}) {
        function grouping_function(base_line, tax_data) {
            return {
                is_refund: base_line.is_refund,
                currency: base_line.currency_id,
                computation_key: base_line.computation_key,
            }
        }

        const base_lines_aggregated_values = this.aggregate_base_lines_tax_details(
            base_lines,
            grouping_function
        );
        const values_per_grouping_key = this.aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        );
        for (const values of Object.values(values_per_grouping_key)) {
            const grouping_key = values.grouping_key;
            let current_mode = mode;
            if (current_mode === "mixed") {
                current_mode = "included";
                for (const base_line_taxes_data of values.base_line_x_taxes_data) {
                    const taxes_data = base_line_taxes_data[1];
                    if (taxes_data.some((tax_data) => !tax_data.price_include)) {
                        current_mode = "excluded";
                        break;
                    }
                }
            }

            const currency = grouping_key.currency;
            for (const [delta_currency_indicator, delta_currency] of [
                ["_currency", currency],
                ["", company.currency_id],
            ]) {
                let delta_total_excluded = 0.0;
                let target_factors = [];
                if (current_mode === "excluded") {
                    // Price-excluded rounding.
                    const raw_total_excluded =
                        values[`target_total_excluded${delta_currency_indicator}`];
                    if (!raw_total_excluded) {
                        continue;
                    }

                    const rounded_raw_total_excluded = roundPrecision(
                        raw_total_excluded,
                        delta_currency.rounding
                    );
                    const total_excluded = values[`total_excluded${delta_currency_indicator}`];
                    delta_total_excluded = rounded_raw_total_excluded - total_excluded;
                    target_factors = values.base_line_x_taxes_data.map(([base_line]) => ({
                        factor: base_line.tax_details[
                            `raw_total_excluded${delta_currency_indicator}`
                        ],
                        base_line: base_line,
                    }));
                } else {
                    // Price-included rounding.
                    const raw_total_included =
                        values[`target_total_excluded${delta_currency_indicator}`] +
                        values[`target_tax_amount${delta_currency_indicator}`];
                    if (!raw_total_included) {
                        continue;
                    }
                    const rounded_raw_total_included = roundPrecision(
                        raw_total_included,
                        delta_currency.rounding
                    );
                    const total_included =
                        values[`total_excluded${delta_currency_indicator}`] +
                        values[`tax_amount${delta_currency_indicator}`];
                    delta_total_excluded = rounded_raw_total_included - total_included;
                    target_factors = values.base_line_x_taxes_data.map(([base_line]) => ({
                        factor: base_line.tax_details[
                            `raw_total_included${delta_currency_indicator}`
                        ],
                        base_line: base_line,
                    }));
                }

                const amounts_to_distribute = this.distribute_delta_amount_smoothly(
                    delta_currency.decimal_places,
                    delta_total_excluded,
                    target_factors
                );
                for (let i = 0; i < target_factors.length; i++) {
                    const base_line = target_factors[i].base_line;
                    const amount_to_distribute = amounts_to_distribute[i];
                    base_line.tax_details[`delta_total_excluded${delta_currency_indicator}`] +=
                        amount_to_distribute;
                }
            }
        }
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    round_base_lines_tax_details(base_lines, company) {
        // Raw rounding.
        for (const base_line of base_lines) {
            const tax_details = base_line.tax_details;

            for (const [suffix, currency] of [
                ["_currency", base_line.currency_id],
                ["", company.currency_id],
            ]) {
                const total_excluded_field = `total_excluded${suffix}`;
                tax_details[total_excluded_field] = roundPrecision(
                    tax_details[`raw_${total_excluded_field}`],
                    currency.rounding
                );

                for (const tax_data of tax_details.taxes_data) {
                    for (const prefix of ["base", "tax"]) {
                        const field = `${prefix}_amount${suffix}`;
                        tax_data[field] = roundPrecision(
                            tax_data[`raw_${field}`],
                            currency.rounding
                        );
                    }
                }
            }
        }

        // Apply 'manual_tax_amounts'.
        for (const base_line of base_lines) {
            const manual_tax_amounts = base_line.manual_tax_amounts;
            const rate = base_line.rate;
            const tax_details = base_line.tax_details;

            for (const [suffix, currency] of [
                ["_currency", base_line.currency_id],
                ["", company.currency_id],
            ]) {
                const total_field = `total_excluded${suffix}`;
                const manual_field = `manual_${total_field}`;
                if (base_line[manual_field] !== null) {
                    tax_details[total_field] = base_line[manual_field];
                    if (suffix === "_currency" && rate) {
                        tax_details.total_excluded = roundPrecision(
                            tax_details[total_field] / rate,
                            company.currency_id.rounding
                        );
                    }
                }

                for (const tax_data of tax_details.taxes_data) {
                    const tax = tax_data.tax;
                    const reverse_charge_sign = tax_data.is_reverse_charge ? -1 : 1;
                    const current_manual_tax_amounts =
                        (manual_tax_amounts && manual_tax_amounts[String(tax.id)]) || {};

                    for (const [prefix, factor] of [
                        ["base", 1],
                        ["tax", reverse_charge_sign],
                    ]) {
                        const field = `${prefix}_amount${suffix}`;
                        if (field in current_manual_tax_amounts) {
                            tax_data[field] = roundPrecision(
                                factor * current_manual_tax_amounts[field],
                                currency.rounding
                            );
                            if (suffix === "_currency" && rate) {
                                tax_data[`${prefix}_amount`] = roundPrecision(
                                    tax_data[field] / rate,
                                    company.currency_id.rounding
                                );
                            }
                        }
                    }
                }
            }
        }

        // Compute 'total_included' & add 'delta_total_excluded'.
        for (const base_line of base_lines) {
            const tax_details = base_line.tax_details;
            for (const suffix of ["_currency", ""]) {
                tax_details[`delta_total_excluded${suffix}`] = 0.0;
                tax_details[`total_included${suffix}`] = tax_details[`total_excluded${suffix}`];
                for (const tax_data of tax_details.taxes_data) {
                    tax_details[`total_included${suffix}`] += tax_data[`tax_amount${suffix}`];
                }
            }
        }

        this.round_tax_details_tax_amounts(base_lines, company);
        this.round_tax_details_base_lines(base_lines, company);
    },

    // -------------------------------------------------------------------------
    // TAX TOTALS SUMMARY
    // -------------------------------------------------------------------------

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    get_tax_totals_summary(base_lines, currency, company, { cash_rounding = null } = {}) {
        const company_pd = company.currency_id.rounding;
        const tax_totals_summary = {
            currency_id: currency.id,
            currency_pd: currency.rounding,
            company_currency_id: company.currency_id.id,
            company_currency_pd: company.currency_id.rounding,
            has_tax_groups: false,
            subtotals: [],
            base_amount_currency: 0.0,
            base_amount: 0.0,
            tax_amount_currency: 0.0,
            tax_amount: 0.0,
        };

        // Global tax values.
        const global_grouping_function = (base_line, tax_data) => tax_data !== null;

        let base_lines_aggregated_values = this.aggregate_base_lines_tax_details(
            base_lines,
            global_grouping_function
        );
        let values_per_grouping_key = this.aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        );

        for (const values of Object.values(values_per_grouping_key)) {
            if (values.grouping_key) {
                tax_totals_summary.has_tax_groups = true;
            }
            tax_totals_summary.base_amount_currency += values.total_excluded_currency;
            tax_totals_summary.base_amount += values.total_excluded;
            tax_totals_summary.tax_amount_currency += values.tax_amount_currency;
            tax_totals_summary.tax_amount += values.tax_amount;
        }

        // Tax groups.
        const untaxed_amount_subtotal_label = _t("Untaxed Amount");
        const subtotals = {};

        const tax_group_grouping_function = (base_line, tax_data) => {
            if (!tax_data) {
                return;
            }
            return tax_data.tax.tax_group_id;
        }

        base_lines_aggregated_values = this.aggregate_base_lines_tax_details(
            base_lines,
            tax_group_grouping_function
        );
        values_per_grouping_key = this.aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        );

        const sorted_total_per_tax_group = Object.values(values_per_grouping_key)
            .filter((values) => values.grouping_key)
            .sort(
                (a, b) =>
                    a.grouping_key.sequence - b.grouping_key.sequence ||
                    a.grouping_key.id - b.grouping_key.id
            );

        const encountered_base_amounts = new Set();
        const subtotals_order = {};

        for (const [order, values] of sorted_total_per_tax_group.entries()) {
            const tax_group = values.grouping_key;

            // Get all involved taxes in the tax group.
            const involved_tax_ids = new Set();
            const involved_amount_types = new Set();
            const involved_price_include = new Set();
            values.base_line_x_taxes_data.forEach(([base_line, taxes_data]) => {
                taxes_data.forEach((tax_data) => {
                    const tax = tax_data.tax;
                    involved_tax_ids.add(tax.id);
                    involved_amount_types.add(tax.amount_type);
                    involved_price_include.add(tax.price_include);
                });
            });

            // Compute the display base amounts.
            let display_base_amount;
            let display_base_amount_currency;
            if (involved_amount_types.size === 1 && involved_amount_types.has("fixed")) {
                display_base_amount = false;
                display_base_amount_currency = false;
            } else if (
                involved_amount_types.size === 1 &&
                involved_amount_types.has("division") &&
                involved_price_include.size === 1 &&
                involved_price_include.has(true)
            ) {
                display_base_amount = 0.0;
                display_base_amount_currency = 0.0;
                values.base_line_x_taxes_data.forEach(([base_line, _taxes_data]) => {
                    const tax_details = base_line.tax_details;
                    display_base_amount +=
                        tax_details.total_excluded + tax_details.delta_total_excluded;
                    display_base_amount_currency +=
                        tax_details.total_excluded_currency +
                        tax_details.delta_total_excluded_currency;
                    for (const tax_data of tax_details.taxes_data) {
                        display_base_amount_currency += tax_data.tax_amount_currency;
                        display_base_amount += tax_data.tax_amount;
                    }
                });
            } else {
                display_base_amount = values.base_amount;
                display_base_amount_currency = values.base_amount_currency;
            }

            if (typeof display_base_amount_currency === "number") {
                encountered_base_amounts.add(
                    parseFloat(display_base_amount_currency.toFixed(currency.decimal_places))
                );
            }

            // Order of the subtotals.
            const preceding_subtotal =
                tax_group.preceding_subtotal || untaxed_amount_subtotal_label;
            if (!(preceding_subtotal in subtotals)) {
                subtotals[preceding_subtotal] = {
                    tax_groups: [],
                    tax_amount_currency: 0.0,
                    tax_amount: 0.0,
                    base_amount_currency: 0.0,
                    base_amount: 0.0,
                };
            }
            if (!(preceding_subtotal in subtotals_order)) {
                subtotals_order[preceding_subtotal] = order;
            }

            subtotals[preceding_subtotal].tax_groups.push({
                id: tax_group.id,
                involved_tax_ids: Array.from(involved_tax_ids),
                tax_amount_currency: values.tax_amount_currency,
                tax_amount: values.tax_amount,
                base_amount_currency: values.base_amount_currency,
                base_amount: values.base_amount,
                display_base_amount_currency,
                display_base_amount,
                group_name: tax_group.name,
                group_label: tax_group.pos_receipt_label,
            });
        }

        // Subtotals.
        if (!Object.keys(subtotals).length) {
            subtotals[untaxed_amount_subtotal_label] = {
                tax_groups: [],
                tax_amount_currency: 0.0,
                tax_amount: 0.0,
                base_amount_currency: 0.0,
                base_amount: 0.0,
            };
        }

        const ordered_subtotals = Array.from(Object.entries(subtotals)).sort(
            (a, b) => (subtotals_order[a[0]] || 0) - (subtotals_order[b[0]] || 0)
        );
        let accumulated_tax_amount_currency = 0.0;
        let accumulated_tax_amount = 0.0;
        for (const [subtotal_label, subtotal] of ordered_subtotals) {
            subtotal.name = subtotal_label;
            subtotal.base_amount_currency =
                tax_totals_summary.base_amount_currency + accumulated_tax_amount_currency;
            subtotal.base_amount = tax_totals_summary.base_amount + accumulated_tax_amount;
            for (const tax_group of subtotal.tax_groups) {
                subtotal.tax_amount_currency += tax_group.tax_amount_currency;
                subtotal.tax_amount += tax_group.tax_amount;
                accumulated_tax_amount_currency += tax_group.tax_amount_currency;
                accumulated_tax_amount += tax_group.tax_amount;
            }
            tax_totals_summary.subtotals.push(subtotal);
        }

        // Cash rounding
        const cash_rounding_lines = base_lines.filter(
            (base_line) => base_line.special_type === "cash_rounding"
        );
        if (cash_rounding_lines.length) {
            tax_totals_summary.cash_rounding_base_amount_currency = 0.0;
            tax_totals_summary.cash_rounding_base_amount = 0.0;
            cash_rounding_lines.forEach((base_line) => {
                const tax_details = base_line.tax_details;
                tax_totals_summary.cash_rounding_base_amount_currency +=
                    tax_details.total_excluded_currency;
                tax_totals_summary.cash_rounding_base_amount += tax_details.total_excluded;
            });
        } else if (cash_rounding !== null) {
            const strategy = cash_rounding.strategy;
            const cash_rounding_pd = cash_rounding.rounding;
            const cash_rounding_method = cash_rounding.rounding_method;
            const total_amount_currency =
                tax_totals_summary.base_amount_currency + tax_totals_summary.tax_amount_currency;
            const total_amount = tax_totals_summary.base_amount + tax_totals_summary.tax_amount;
            const expected_total_amount_currency = roundPrecision(
                total_amount_currency,
                cash_rounding_pd,
                cash_rounding_method
            );
            let cash_rounding_base_amount_currency =
                expected_total_amount_currency - total_amount_currency;
            const rate = total_amount ? Math.abs(total_amount_currency / total_amount) : 0.0;
            let cash_rounding_base_amount = rate
                ? roundPrecision(cash_rounding_base_amount_currency / rate, company_pd)
                : 0.0;
            if (!floatIsZero(cash_rounding_base_amount_currency, currency.decimal_places)) {
                if (strategy === "add_invoice_line") {
                    tax_totals_summary.cash_rounding_base_amount_currency =
                        cash_rounding_base_amount_currency;
                    tax_totals_summary.cash_rounding_base_amount = cash_rounding_base_amount;
                    tax_totals_summary.base_amount_currency += cash_rounding_base_amount_currency;
                    tax_totals_summary.base_amount += cash_rounding_base_amount;
                    subtotals[untaxed_amount_subtotal_label].base_amount_currency +=
                        cash_rounding_base_amount_currency;
                    subtotals[untaxed_amount_subtotal_label].base_amount +=
                        cash_rounding_base_amount;
                } else if (strategy === "biggest_tax") {
                    const all_subtotal_tax_group = tax_totals_summary.subtotals.flatMap(
                        (subtotal) => subtotal.tax_groups.map((tax_group) => [subtotal, tax_group])
                    );

                    if (all_subtotal_tax_group.length) {
                        const [max_subtotal, max_tax_group] = all_subtotal_tax_group.reduce(
                            (a, b) => (b[1].tax_amount_currency > a[1].tax_amount_currency ? b : a)
                        );

                        max_tax_group.tax_amount_currency += cash_rounding_base_amount_currency;
                        max_tax_group.tax_amount += cash_rounding_base_amount;
                        max_subtotal.tax_amount_currency += cash_rounding_base_amount_currency;
                        max_subtotal.tax_amount += cash_rounding_base_amount;
                        tax_totals_summary.tax_amount_currency +=
                            cash_rounding_base_amount_currency;
                        tax_totals_summary.tax_amount += cash_rounding_base_amount;
                    } else {
                        // Failed to apply the cash rounding since there is no tax.
                        cash_rounding_base_amount_currency = 0.0;
                        cash_rounding_base_amount = 0.0;
                    }
                }
            }
        }

        // Subtract the cash rounding from the untaxed amounts.
        const cash_rounding_base_amount_currency =
            tax_totals_summary.cash_rounding_base_amount_currency || 0.0;
        const cash_rounding_base_amount = tax_totals_summary.cash_rounding_base_amount || 0.0;
        tax_totals_summary.base_amount_currency -= cash_rounding_base_amount_currency;
        tax_totals_summary.base_amount -= cash_rounding_base_amount;
        for (const subtotal of tax_totals_summary.subtotals) {
            subtotal.base_amount_currency -= cash_rounding_base_amount_currency;
            subtotal.base_amount -= cash_rounding_base_amount;
        }
        encountered_base_amounts.add(
            parseFloat(tax_totals_summary.base_amount_currency.toFixed(currency.decimal_places))
        );
        tax_totals_summary.same_tax_base = encountered_base_amounts.size === 1;

        // Total amount.
        tax_totals_summary.total_amount_currency =
            tax_totals_summary.base_amount_currency +
            tax_totals_summary.tax_amount_currency +
            cash_rounding_base_amount_currency;
        tax_totals_summary.total_amount =
            tax_totals_summary.base_amount +
            tax_totals_summary.tax_amount +
            cash_rounding_base_amount;

        return tax_totals_summary;
    },

    // -------------------------------------------------------------------------
    // AGGREGATOR OF TAX DETAILS
    // -------------------------------------------------------------------------

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    aggregate_base_line_tax_details(base_line, grouping_function) {
        const values_per_grouping_key = {};
        const tax_details = base_line.tax_details;
        const taxes_data = tax_details.taxes_data;
        const manual_tax_amounts = base_line.manual_tax_amounts;

        // If there are no taxes, we pass an empty object to the grouping function.
        for (const tax_data of taxes_data.length !== 0 ? taxes_data : [null]) {
            const current_manual_tax_amounts =
                tax_data && manual_tax_amounts
                    ? manual_tax_amounts[tax_data.tax.id.toString()] || {}
                    : {};

            let raw_grouping_key = grouping_function(base_line, tax_data);
            let grouping_key;
            if (raw_grouping_key && typeof raw_grouping_key === "object" && "raw_grouping_key" in raw_grouping_key) {
                // TODO: TO BE REMOVED IN MASTER (here for retro-compatibility)
                // There is no FrozenDict in javascript.
                // When the key is a record, it can't be jsonified so this is a trick to provide both the
                // raw_grouping_key (to be jsonified) from the grouping_key (to be added to the values).
                raw_grouping_key = raw_grouping_key.raw_grouping_key;
                grouping_key = raw_grouping_key.grouping_key;

                // Handle dictionary-like keys (converted to string in JS)
                if (typeof grouping_key === "object") {
                    grouping_key = JSON.stringify(grouping_key);
                }
            } else {
                grouping_key = this.stringify_grouping_key(raw_grouping_key);
            }

            // Base amount.
            if (!(grouping_key in values_per_grouping_key)) {
                const values = {
                    grouping_key: raw_grouping_key,
                    taxes_data: [],
                };
                values_per_grouping_key[grouping_key] = values;

                for (const suffix of ["_currency", ""]) {
                    const excluded_rounded_field = `total_excluded${suffix}`;
                    const excluded_delta_field = `delta_${excluded_rounded_field}`;
                    const excluded_raw_field = `raw_${excluded_rounded_field}`;
                    const excluded_target_field = `target_${excluded_rounded_field}`;
                    const excluded_manual_field = `manual_${excluded_rounded_field}`;

                    const excluded_rounded_amount =
                        tax_details[excluded_rounded_field] + tax_details[excluded_delta_field];
                    const excluded_raw_amount = tax_details[excluded_raw_field];

                    values[excluded_rounded_field] = excluded_rounded_amount;
                    values[excluded_raw_field] = excluded_raw_amount;

                    let excluded_target_amount;
                    if (base_line[excluded_manual_field] !== null) {
                        excluded_target_amount = base_line[excluded_manual_field];
                    } else if (suffix === "" && base_line.manual_total_excluded_currency !== null) {
                        excluded_target_amount = excluded_rounded_amount;
                    } else {
                        excluded_target_amount = excluded_raw_amount;
                    }
                    values[excluded_target_field] = excluded_target_amount;

                    const tax_base_rounded_field = `base_amount${suffix}`;
                    const tax_base_raw_field = `raw_${tax_base_rounded_field}`;
                    const tax_base_target_field = `target_${tax_base_rounded_field}`;

                    if (tax_data) {
                        values[tax_base_rounded_field] = tax_data[tax_base_rounded_field];
                        values[tax_base_raw_field] = tax_data[tax_base_raw_field];

                        if (tax_base_rounded_field in current_manual_tax_amounts) {
                            values[tax_base_target_field] =
                                current_manual_tax_amounts[tax_base_rounded_field];
                        } else if (
                            suffix === "" &&
                            "base_amount_currency" in current_manual_tax_amounts
                        ) {
                            values[tax_base_target_field] = tax_data[tax_base_rounded_field];
                        } else {
                            values[tax_base_target_field] = tax_data[tax_base_raw_field];
                        }
                    } else {
                        values[tax_base_rounded_field] = excluded_rounded_amount;
                        values[tax_base_raw_field] = excluded_raw_amount;
                        values[tax_base_target_field] = excluded_target_amount;
                    }

                    const tax_rounded_field = `tax_amount${suffix}`;
                    const tax_raw_field = `raw_${tax_rounded_field}`;
                    const tax_target_field = `target_${tax_rounded_field}`;

                    values[tax_rounded_field] = 0.0;
                    values[tax_raw_field] = 0.0;
                    values[tax_target_field] = 0.0;
                }
            }

            // Tax amount.
            if (tax_data) {
                const reverse_charge_sign = tax_data.is_reverse_charge ? -1 : 1;
                const values = values_per_grouping_key[grouping_key];
                for (const suffix of ["_currency", ""]) {
                    const tax_rounded_field = `tax_amount${suffix}`;
                    const tax_raw_field = `raw_${tax_rounded_field}`;
                    const tax_target_field = `target_${tax_rounded_field}`;

                    values[tax_rounded_field] += tax_data[tax_rounded_field];
                    values[tax_raw_field] += tax_data[tax_raw_field];

                    if (tax_rounded_field in current_manual_tax_amounts) {
                        values[tax_target_field] +=
                            reverse_charge_sign * current_manual_tax_amounts[tax_rounded_field];
                    } else if (
                        suffix === "" &&
                        "tax_amount_currency" in current_manual_tax_amounts
                    ) {
                        values[tax_target_field] = tax_data[tax_rounded_field];
                    } else {
                        values[tax_target_field] += tax_data[tax_raw_field];
                    }
                }
                values.taxes_data.push(tax_data);
            }
        }
        return values_per_grouping_key;
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    aggregate_base_lines_tax_details(base_lines, grouping_function) {
        return base_lines.map((base_line) => [
            base_line,
            this.aggregate_base_line_tax_details(base_line, grouping_function),
        ]);
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    aggregate_base_lines_aggregated_values(base_lines_aggregated_values) {
        const default_float_fields = new Set();
        for (const prefix of ["", "raw_", "target_"]) {
            for (const suffix of ["_currency", ""]) {
                for (const field of ["base_amount", "tax_amount", "total_excluded"]) {
                    default_float_fields.add(`${prefix}${field}${suffix}`);
                }
            }
        }

        const values_per_grouping_key = {};
        for (const [base_line, aggregated_values] of base_lines_aggregated_values) {
            for (const [raw_grouping_key, values] of Object.entries(aggregated_values)) {
                const grouping_key = values.grouping_key;

                if (!(raw_grouping_key in values_per_grouping_key)) {
                    const initial_values = (values_per_grouping_key[raw_grouping_key] = {
                        base_line_x_taxes_data: [],
                        grouping_key: grouping_key,
                    });
                    default_float_fields.forEach((field) => {
                        initial_values[field] = 0.0;
                    });
                }
                const agg_values = values_per_grouping_key[raw_grouping_key];
                default_float_fields.forEach((field) => {
                    agg_values[field] += values[field];
                });
                agg_values.base_line_x_taxes_data.push([base_line, values.taxes_data]);
            }
        }
        return values_per_grouping_key;
    },

    // -------------------------------------------------------------------------
    // ADVANCED LINES MANIPULATION HELPERS
    // -------------------------------------------------------------------------

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    can_be_discounted(tax) {
        return !["fixed", "code"].includes(tax.amount_type);
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    merge_tax_details(tax_details_1, tax_details_2) {
        const results = {};
        for (const prefix of ["raw_", ""]) {
            for (const field of ["total_excluded", "total_included"]) {
                for (const suffix of ["_currency", ""]) {
                    const key = `${prefix}${field}${suffix}`;
                    results[key] = tax_details_1[key] + tax_details_2[key];
                }
            }
        }
        for (const suffix of ["_currency", ""]) {
            const field = `delta_total_excluded${suffix}`;
            results[field] = tax_details_1[field] + tax_details_2[field];
        }

        const agg_taxes_data = {};
        for (const tax_details of [tax_details_1, tax_details_2]) {
            for (const tax_data of tax_details.taxes_data) {
                const tax = tax_data.tax;
                const tax_id_str = tax.id.toString();
                if (tax_id_str in agg_taxes_data) {
                    const agg_tax_data = agg_taxes_data[tax_id_str];
                    for (const prefix of ["raw_", ""]) {
                        for (const suffix of ["_currency", ""]) {
                            for (const field of ["base_amount", "tax_amount"]) {
                                const field_with_prefix = `${prefix}${field}${suffix}`;
                                agg_tax_data[field_with_prefix] += tax_data[field_with_prefix];
                            }
                        }
                    }
                } else {
                    agg_taxes_data[tax_id_str] = { ...tax_data };
                }
            }
        }
        results.taxes_data = Object.values(agg_taxes_data);

        // In case there is some taxes that are in tax_details_1 but not on tax_details_2,
        // we have to shift manually the base amount. It happens with fixed taxes in which the base
        // is meaningless but still used in the computations.
        const taxes_data_in_2 = new Set(tax_details_2.taxes_data.map((td) => td.tax.id));
        const not_discountable_taxes_data = new Set(
            tax_details_1.taxes_data
                .filter((td) => !taxes_data_in_2.has(td.tax.id))
                .map((td) => td.tax.id)
        );
        for (const tax_data of results.taxes_data) {
            if (not_discountable_taxes_data.has(tax_data.tax.id)) {
                for (const suffix of ["_currency", ""]) {
                    for (const prefix of ["raw_", ""]) {
                        tax_data[`${prefix}base_amount${suffix}`] +=
                            tax_details_2[`${prefix}total_excluded${suffix}`];
                    }
                    tax_data[`base_amount${suffix}`] +=
                        tax_details_2[`delta_total_excluded${suffix}`];
                }
            }
        }

        return results;
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    fix_base_lines_tax_details_on_manual_tax_amounts(
        base_lines,
        company,
        { filter_function = null } = {}
    ) {
        for (const base_line of base_lines) {
            const tax_details = base_line.tax_details;
            const taxes_data = tax_details.taxes_data;
            if (!taxes_data.length) {
                continue;
            }

            base_line.manual_total_excluded_currency =
                tax_details.total_excluded_currency + tax_details.delta_total_excluded_currency;
            base_line.manual_total_excluded =
                tax_details.total_excluded + tax_details.delta_total_excluded;
            base_line.manual_tax_amounts = {};
            for (const tax_data of taxes_data) {
                const tax = tax_data.tax;
                const tax_id_str = tax.id.toString();
                base_line.manual_tax_amounts[tax_id_str] = {};
                if (filter_function && !filter_function(base_line, tax_data)) {
                    continue;
                }

                base_line.manual_tax_amounts[tax_id_str] = {
                    tax_amount_currency: tax_data.tax_amount_currency,
                    tax_amount: tax_data.tax_amount,
                    base_amount_currency: tax_data.base_amount_currency,
                    base_amount: tax_data.base_amount,
                };
            }
        }
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     * DEPRECATED: TO BE REMOVED IN MASTER
     */
    compute_subset_base_lines_total(base_lines, company) {
        let base_amount_currency = 0.0;
        let tax_amount_currency = 0.0;
        let base_amount = 0.0;
        let tax_amount = 0.0;
        const tax_amounts_mapping = {};
        let raw_total_included_currency = 0.0;
        let raw_total_included = 0.0;
        for (const base_line of base_lines) {
            const tax_details = base_line.tax_details;
            base_amount_currency +=
                tax_details.total_excluded_currency + tax_details.delta_total_excluded_currency;
            base_amount += tax_details.total_excluded + tax_details.delta_total_excluded;
            raw_total_included_currency += tax_details.raw_total_excluded_currency;
            raw_total_included += tax_details.raw_total_excluded;
            for (const tax_data of tax_details.taxes_data) {
                const tax = tax_data.tax;
                if (!this.can_be_discounted(tax)) {
                    continue;
                }

                const tax_id_str = tax.id.toString();
                if (!(tax_id_str in tax_amounts_mapping)) {
                    tax_amounts_mapping[tax_id_str] = {
                        tax_amount_currency: 0.0,
                        tax_amount: 0.0,
                    };
                }

                tax_amount_currency += tax_data.tax_amount_currency;
                tax_amount += tax_data.tax_amount;
                tax_amounts_mapping[tax_id_str].tax_amount_currency += tax_data.tax_amount_currency;
                tax_amounts_mapping[tax_id_str].tax_amount += tax_data.tax_amount;
                raw_total_included_currency += tax_data.raw_tax_amount_currency;
                raw_total_included += tax_data.raw_tax_amount;
            }
        }
        return {
            base_amount_currency: base_amount_currency,
            tax_amount_currency: tax_amount_currency,
            base_amount: base_amount,
            tax_amount: tax_amount,
            tax_amounts_mapping: tax_amounts_mapping,
            raw_total_included_currency: raw_total_included_currency,
            raw_total_included: raw_total_included,
            rate: raw_total_included ? raw_total_included_currency / raw_total_included : 0.0,
        };
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    reduce_base_lines_with_grouping_function(
        base_lines,
        { grouping_function = null, aggregate_function = null, computation_key = null } = {}
    ) {
        const base_line_map = {};
        for (const base_line of base_lines) {
            const price_unit_after_discount =
                base_line.price_unit * (1 - base_line.discount / 100.0);
            const new_base_line = this.prepare_base_line_for_taxes_computation(base_line, {
                price_unit: base_line.quantity * price_unit_after_discount,
                quantity: 1.0,
                discount: 0.0,
            });
            const raw_grouping_key = {
                tax_ids: new_base_line.tax_ids.map((tax) => tax.id),
                computation_key: base_line.computation_key,
            };
            const grouping_key = {
                tax_ids: new_base_line.tax_ids.map((tax) => tax),
                computation_key: base_line.computation_key,
            };
            if (grouping_function) {
                const generated_grouping_key = grouping_function(new_base_line);

                // There is no FrozenDict in javascript.
                // When the key is a record, it can't be jsonified so this is a trick to provide both the
                // raw_grouping_key (to be jsonified) from the grouping_key (to be added to the values).
                if ("raw_grouping_key" in generated_grouping_key) {
                    Object.assign(raw_grouping_key, generated_grouping_key.raw_grouping_key);
                    Object.assign(grouping_key, generated_grouping_key.grouping_key);
                } else {
                    Object.assign(raw_grouping_key, generated_grouping_key);
                    Object.assign(grouping_key, generated_grouping_key);
                }
            }

            const grouping_key_json = JSON.stringify(raw_grouping_key);
            let target_base_line = base_line_map[grouping_key_json];
            if (target_base_line) {
                target_base_line.price_unit += new_base_line.price_unit;
                target_base_line.tax_details = this.merge_tax_details(
                    target_base_line.tax_details,
                    base_line.tax_details
                );
                if (aggregate_function) {
                    aggregate_function(target_base_line, base_line);
                }
            } else {
                base_line_map[grouping_key_json] = this.prepare_base_line_for_taxes_computation(
                    new_base_line,
                    {
                        ...grouping_key,
                        computation_key: computation_key,
                        tax_details: {
                            ...base_line.tax_details,
                            taxes_data: base_line.tax_details.taxes_data.map((tax_data) =>
                                Object.assign({}, tax_data)
                            ),
                        },
                    }
                );
                target_base_line = base_line_map[grouping_key_json];
            }
        }

        // Remove zero lines.
        const reduced_base_lines = Object.values(base_line_map).filter(
            (base_line) => !floatIsZero(base_line.price_unit, base_line.currency_id.decimal_places)
        );
        return reduced_base_lines;
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     * DEPRECATED: TO BE REMOVED IN MASTER
     */
    apply_base_lines_manual_amounts_to_reach(
        base_lines,
        company,
        target_base_amount_currency,
        target_base_amount,
        target_tax_amounts_mapping
    ) {
        const currency = base_lines[0].currency_id;

        // Smooth distribution of the delta accross the base line, starting at the biggest one.
        const sorted_base_lines = base_lines.sort((base_line_1, base_line_2) => {
            const key_1 = [
                Boolean(base_line_1.special_type),
                -base_line_1.tax_details.total_excluded_currency,
            ];
            const key_2 = [
                Boolean(base_line_2.special_type),
                -base_line_2.tax_details.total_excluded_currency,
            ];

            if (key_1[0] !== key_2[0]) {
                return key_1[0] - key_2[0];
            }
            return key_1[1] - key_2[1];
        });
        const base_lines_totals = this.compute_subset_base_lines_total(base_lines, company);
        for (const [delta_suffix, delta_target_base_amount, delta_currency] of [
            ["_currency", target_base_amount_currency, currency],
            ["", target_base_amount, company.currency_id],
        ]) {
            const target_factors = sorted_base_lines.map((base_line) => ({
                factor: Math.abs(
                    (base_line.tax_details.total_excluded_currency +
                        base_line.tax_details.delta_total_excluded_currency) /
                        base_lines_totals.base_amount_currency
                ),
                base_line: base_line,
            }));
            const amounts_to_distribute = this.distribute_delta_amount_smoothly(
                delta_currency.decimal_places,
                delta_target_base_amount - base_lines_totals[`base_amount${delta_suffix}`],
                target_factors
            );
            for (let i = 0; i < target_factors.length; i++) {
                const target_factor = target_factors[i];
                const amount_to_distribute = amounts_to_distribute[i];
                const base_line = target_factor.base_line;
                const tax_details = base_line.tax_details;
                const taxes_data = tax_details.taxes_data;
                if (delta_suffix === "_currency") {
                    base_line.price_unit +=
                        amount_to_distribute / Math.abs(base_line.quantity || 1.0);
                }
                if (!taxes_data.length) {
                    continue;
                }

                const first_batch = taxes_data[0].batch;
                for (const tax_data of taxes_data) {
                    const tax = tax_data.tax;
                    if (first_batch.includes(tax)) {
                        tax_data[`base_amount${delta_suffix}`] += amount_to_distribute;
                    } else {
                        break;
                    }
                }
            }
        }

        for (const [tax_id_str, tax_amounts] of Object.entries(target_tax_amounts_mapping)) {
            for (const [delta_suffix, delta_target_tax_amount, delta_currency] of [
                ["_currency", tax_amounts.tax_amount_currency, currency],
                ["", tax_amounts.tax_amount, company.currency_id],
            ]) {
                const current_tax_amounts = base_lines_totals.tax_amounts_mapping[tax_id_str];
                if (!current_tax_amounts.tax_amount_currency) {
                    continue;
                }

                const target_factors = [];
                for (const base_line of sorted_base_lines) {
                    for (const tax_data of base_line.tax_details.taxes_data) {
                        if (tax_data.tax.id.toString() === tax_id_str) {
                            target_factors.push({
                                factor: Math.abs(
                                    tax_data.tax_amount_currency /
                                        current_tax_amounts.tax_amount_currency
                                ),
                                tax_data: tax_data,
                            });
                        }
                    }
                }
                const amounts_to_distribute = this.distribute_delta_amount_smoothly(
                    delta_currency.decimal_places,
                    delta_target_tax_amount - current_tax_amounts[`tax_amount${delta_suffix}`],
                    target_factors
                );
                for (let i = 0; i < target_factors.length; i++) {
                    const target_factor = target_factors[i];
                    const amount_to_distribute = amounts_to_distribute[i];
                    const tax_data = target_factor.tax_data;
                    tax_data[`tax_amount${delta_suffix}`] += amount_to_distribute;
                }
            }
        }

        this.fix_base_lines_tax_details_on_manual_tax_amounts(base_lines, company);
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    reduce_base_lines_to_target_amount(
        base_lines,
        company,
        amount_type,
        amount,
        { computation_key = null, grouping_function = null, aggregate_function = null } = {}
    ) {
        if (!base_lines.length) {
            return [];
        }

        const currency = base_lines[0].currency_id;
        const rate = base_lines[0].rate;

        // Compute the current total amount of the base lines.
        function grouping_function_total(base_line, tax_data) {
            return true;
        }

        let base_lines_aggregated_values = this.aggregate_base_lines_tax_details(
            base_lines,
            grouping_function_total
        );
        let values_per_grouping_key = this.aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        );
        const total_amount_currency = Object.values(values_per_grouping_key).reduce(
            (acc, values) => acc + values.total_excluded_currency + values.tax_amount_currency,
            0
        );
        const total_amount = Object.values(values_per_grouping_key).reduce(
            (acc, values) => acc + values.total_excluded + values.tax_amount,
            0
        );

        // Compute the current total tax amount per tax.
        function grouping_function_tax(base_line, tax_data) {
            return tax_data ? tax_data.tax.id.toString() : null;
        }

        base_lines_aggregated_values = this.aggregate_base_lines_tax_details(
            base_lines,
            grouping_function_tax
        );
        values_per_grouping_key = this.aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        );
        const tax_amounts_per_tax = {};
        for (const [grouping_key, values] of Object.entries(values_per_grouping_key)) {
            if (!grouping_key) {
                continue;
            }

            tax_amounts_per_tax[grouping_key] = {
                tax_amount_currency: values.tax_amount_currency,
                tax_amount: values.tax_amount,
                base_amount_currency: values.base_amount_currency,
                base_amount: values.base_amount,
            };
        }

        // Turn the 'amount_type' / 'amount' into a percentage and the total amounts to be reached
        // from the base lines.
        const sign = amount < 0.0 ? -1 : 1;
        const signed_amount = sign * amount;
        let percentage, expected_total_amount_currency, expected_total_amount;
        if (amount_type === "fixed") {
            percentage = total_amount_currency ? signed_amount / total_amount_currency : 0.0;
            expected_total_amount_currency = roundPrecision(amount, currency.rounding);
            expected_total_amount = rate
                ? roundPrecision(
                      expected_total_amount_currency / rate,
                      company.currency_id.rounding
                  )
                : 0.0;
        } else {
            percentage = signed_amount / 100.0;
            expected_total_amount_currency = roundPrecision(
                total_amount_currency * sign * percentage,
                currency.rounding
            );
            expected_total_amount = roundPrecision(
                total_amount * sign * percentage,
                company.currency_id.rounding
            );
        }

        // Compute the expected amounts.
        const expected_tax_amounts = {};
        for (const [grouping_key, values] of Object.entries(tax_amounts_per_tax)) {
            expected_tax_amounts[grouping_key] = {
                tax_amount_currency: roundPrecision(
                    values.tax_amount_currency * sign * percentage,
                    currency.rounding
                ),
                tax_amount: roundPrecision(
                    values.tax_amount * sign * percentage,
                    company.currency_id.rounding
                ),
                base_amount_currency: roundPrecision(
                    values.base_amount_currency * sign * percentage,
                    currency.rounding
                ),
                base_amount: roundPrecision(
                    values.base_amount * sign * percentage,
                    company.currency_id.rounding
                ),
            };
        }
        const expected_base_amount_currency =
            expected_total_amount_currency -
            Object.values(expected_tax_amounts).reduce((acc, v) => acc + v.tax_amount_currency, 0);
        const expected_base_amount =
            expected_total_amount -
            Object.values(expected_tax_amounts).reduce((acc, v) => acc + v.tax_amount, 0);

        // Reduce the base lines to minimize the number of lines.
        const reduced_base_lines = this.reduce_base_lines_with_grouping_function(base_lines, {
            grouping_function: grouping_function,
            aggregate_function: aggregate_function,
            computation_key: computation_key,
        });

        // Reduce the unit price to approach the target amount.
        const new_base_lines = reduced_base_lines.map((base_line) =>
            this.prepare_base_line_for_taxes_computation(base_line, {
                price_unit: base_line.price_unit * sign * percentage,
                computation_key: computation_key,
            })
        );
        this.add_tax_details_in_base_lines(new_base_lines, company);
        this.round_base_lines_tax_details(new_base_lines, company);

        // Smooth distribution of the delta tax/base amounts.
        const sorted_base_lines = new_base_lines.sort((base_line_1, base_line_2) => {
            const key_1 = [
                Boolean(base_line_1.special_type),
                -base_line_1.tax_details.total_excluded_currency,
            ];
            const key_2 = [
                Boolean(base_line_2.special_type),
                -base_line_2.tax_details.total_excluded_currency,
            ];

            if (key_1[0] !== key_2[0]) {
                return key_1[0] - key_2[0];
            }
            return key_1[1] - key_2[1];
        });
        base_lines_aggregated_values = this.aggregate_base_lines_tax_details(
            new_base_lines,
            grouping_function_tax
        );
        values_per_grouping_key = this.aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        );
        const current_tax_amounts_per_tax = {};
        for (const [grouping_key, values] of Object.entries(values_per_grouping_key)) {
            if (!grouping_key) {
                continue;
            }
            current_tax_amounts_per_tax[grouping_key] = {
                tax_amount_currency: values.tax_amount_currency,
                tax_amount: values.tax_amount,
                base_amount_currency: values.base_amount_currency,
                base_amount: values.base_amount,
            };
        }
        for (const [tax_id_str, tax_amounts] of Object.entries(current_tax_amounts_per_tax)) {
            const tax_amount_currency = tax_amounts.tax_amount_currency;
            if (!tax_amount_currency) {
                continue;
            }

            for (const [delta_suffix, delta_tax_amount, delta_base_amount, delta_currency] of [
                [
                    "_currency",
                    expected_tax_amounts[tax_id_str].tax_amount_currency -
                        tax_amounts.tax_amount_currency,
                    expected_tax_amounts[tax_id_str].base_amount_currency -
                        tax_amounts.base_amount_currency,
                    currency,
                ],
                [
                    "",
                    expected_tax_amounts[tax_id_str].tax_amount - tax_amounts.tax_amount,
                    expected_tax_amounts[tax_id_str].base_amount - tax_amounts.base_amount,
                    company.currency_id,
                ],
            ]) {
                // Tax amount.
                const tax_amount_currency = tax_amounts.tax_amount_currency;
                if (tax_amount_currency) {
                    const target_factors = [];
                    for (const base_line of sorted_base_lines) {
                        for (const tax_data of base_line.tax_details.taxes_data) {
                            if (tax_data.tax.id.toString() === tax_id_str) {
                                target_factors.push({
                                    factor: Math.abs(
                                        tax_data.tax_amount_currency / tax_amount_currency
                                    ),
                                    base_line: base_line,
                                    tax_data: tax_data,
                                });
                            }
                        }
                    }
                    const amounts_to_distribute = this.distribute_delta_amount_smoothly(
                        delta_currency.decimal_places,
                        delta_tax_amount,
                        target_factors
                    );
                    for (const [i, target_factor] of target_factors.entries()) {
                        const amount_to_distribute = amounts_to_distribute[i];
                        target_factor.tax_data[`tax_amount${delta_suffix}`] += amount_to_distribute;
                    }
                }

                // Base amount.
                const base_amount_currency = tax_amounts.base_amount_currency;
                if (base_amount_currency) {
                    const target_factors = [];
                    for (const base_line of sorted_base_lines) {
                        for (const tax_data of base_line.tax_details.taxes_data) {
                            if (tax_data.tax.id.toString() === tax_id_str) {
                                target_factors.push({
                                    factor: Math.abs(
                                        tax_data.base_amount_currency / base_amount_currency
                                    ),
                                    base_line: base_line,
                                    tax_data: tax_data,
                                });
                            }
                        }
                    }
                    const amounts_to_distribute = this.distribute_delta_amount_smoothly(
                        delta_currency.decimal_places,
                        delta_base_amount,
                        target_factors
                    );
                    for (const [i, target_factor] of target_factors.entries()) {
                        const amount_to_distribute = amounts_to_distribute[i];
                        target_factor.tax_data[`base_amount${delta_suffix}`] +=
                            amount_to_distribute;
                    }
                }
            }
        }

        base_lines_aggregated_values = this.aggregate_base_lines_tax_details(
            new_base_lines,
            grouping_function_total
        );
        values_per_grouping_key = this.aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        );
        const current_base_amount_currency = Object.values(values_per_grouping_key).reduce(
            (acc, values) => acc + values.total_excluded_currency,
            0
        );
        const current_base_amount = Object.values(values_per_grouping_key).reduce(
            (acc, values) => acc + values.total_excluded,
            0
        );
        for (const [delta_suffix, delta_base_amount, delta_currency] of [
            ["_currency", expected_base_amount_currency - current_base_amount_currency, currency],
            ["", expected_base_amount - current_base_amount, company.currency_id],
        ]) {
            const target_factors = sorted_base_lines.map((base_line) => ({
                factor: Math.abs(
                    (base_line.tax_details.total_excluded_currency +
                        base_line.tax_details.delta_total_excluded_currency) /
                        current_base_amount_currency
                ),
                base_line: base_line,
            }));
            const amounts_to_distribute = this.distribute_delta_amount_smoothly(
                delta_currency.decimal_places,
                delta_base_amount,
                target_factors
            );
            for (const [i, target_factor] of target_factors.entries()) {
                const base_line = target_factor.base_line;
                const amount_to_distribute = amounts_to_distribute[i];
                const tax_details = base_line.tax_details;
                tax_details[`delta_total_excluded${delta_suffix}`] += amount_to_distribute;
                if (delta_suffix === "_currency") {
                    base_line.price_unit += amount_to_distribute;
                }
            }
        }
        return new_base_lines;
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    partition_base_lines_taxes(base_lines, partition_function) {
        let has_taxes_to_exclude = false;
        const base_lines_partition_taxes = [];
        for (const base_line of base_lines) {
            const tax_details = base_line.tax_details;
            const taxes_data = tax_details.taxes_data;
            const taxes_to_keep = [];
            const taxes_to_exclude = [];
            for (const tax_data of taxes_data) {
                const tax = tax_data.tax;
                if (partition_function(base_line, tax_data)) {
                    taxes_to_keep.push(tax);
                } else {
                    taxes_to_exclude.push(tax);
                }
            }
            if (taxes_to_exclude.length > 0) {
                has_taxes_to_exclude = true;
            }
            base_lines_partition_taxes.push([base_line, taxes_to_keep, taxes_to_exclude]);
        }
        return [base_lines_partition_taxes, has_taxes_to_exclude];
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    prepare_discountable_base_lines(base_lines, company, { exclude_function = null } = {}) {
        function partition_function(base_line, tax_data) {
            const tax = tax_data.tax;
            return (
                this.can_be_discounted(tax) &&
                (!exclude_function || !exclude_function(base_line, tax_data))
            );
        }

        // Exclude non-discountable taxes.
        const base_lines_partition_taxes = this.partition_base_lines_taxes(
            base_lines,
            partition_function.bind(this)
        )[0];
        const discountable_base_lines = [];
        for (const [base_line, taxes_to_keep, taxes_to_exclude] of base_lines_partition_taxes) {
            const tax_details = base_line.tax_details;
            const taxes_data = tax_details.taxes_data;

            if (!taxes_to_exclude.length) {
                discountable_base_lines.push(
                    this.prepare_base_line_for_taxes_computation(base_line, {
                        price_unit:
                            base_line.price_unit *
                            base_line.quantity *
                            (1 - base_line.discount / 100.0),
                        quantity: 1.0,
                        discount: 0.0,
                        manual_tax_amounts: base_line.manual_tax_amounts,
                    })
                );
                continue;
            }

            let taxes_data_for_price_unit;
            if (
                taxes_data.some(
                    (tax_data) =>
                        taxes_to_exclude.includes(tax_data.tax) &&
                        tax_data.tax.price_include &&
                        tax_data.tax.include_base_amount
                )
            ) {
                // When the removed tax affect the base of the others, we had to remove the tax amount applied
                // on those taxes too.
                const discountable_base_line = this.prepare_base_line_for_taxes_computation(
                    base_line,
                    {
                        price_unit: tax_details.raw_total_excluded_currency,
                        quantity: 1.0,
                        discount: 0.0,
                        tax_ids: taxes_to_keep,
                        special_mode: "total_excluded",
                    }
                );
                this.add_tax_details_in_base_line(discountable_base_line, company);
                taxes_data_for_price_unit = discountable_base_line.tax_details.taxes_data;
            } else {
                taxes_data_for_price_unit = taxes_data.filter((tax_data) =>
                    taxes_to_keep.includes(tax_data.tax)
                );
            }

            const price_unit =
                tax_details.raw_total_excluded_currency +
                taxes_data_for_price_unit
                    .filter(
                        (tax_data) =>
                            tax_data.tax.price_include && taxes_to_keep.includes(tax_data.tax)
                    )
                    .reduce((sum, tax_data) => sum + tax_data.raw_tax_amount_currency, 0);
            discountable_base_lines.push(
                this.prepare_base_line_for_taxes_computation(base_line, {
                    price_unit: price_unit,
                    quantity: 1.0,
                    discount: 0.0,
                    tax_ids: taxes_to_keep,
                })
            );
        }
        this.add_tax_details_in_base_lines(discountable_base_lines, company);
        this.round_base_lines_tax_details(discountable_base_lines, company);
        return discountable_base_lines;
    },

    // -------------------------------------------------------------------------
    // GLOBAL DISCOUNT
    // -------------------------------------------------------------------------

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    prepare_global_discount_lines(
        base_lines,
        company,
        amount_type,
        amount,
        { computation_key = "global_discount", grouping_function = null } = {}
    ) {
        const discountable_base_lines = this.prepare_discountable_base_lines(base_lines, company);
        const new_base_lines = this.reduce_base_lines_to_target_amount(
            discountable_base_lines,
            company,
            amount_type,
            -amount,
            { computation_key: computation_key, grouping_function: grouping_function }
        );
        this.fix_base_lines_tax_details_on_manual_tax_amounts(new_base_lines, company);
        return new_base_lines;
    },

    // -------------------------------------------------------------------------
    // DOWN PAYMENT
    // -------------------------------------------------------------------------

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    prepare_base_lines_for_down_payment(base_lines, company, { exclude_function = null } = {}) {
        function partition_function(base_line, tax_data) {
            const tax = tax_data.tax;
            return (
                this.can_be_discounted(tax) &&
                (!exclude_function || !exclude_function(base_line, tax_data))
            );
        }

        const base_lines_partition_taxes = this.partition_base_lines_taxes(
            base_lines,
            partition_function.bind(this)
        )[0];
        const base_lines_for_dp = [];
        for (const [base_line, taxes_to_keep, taxes_to_exclude] of base_lines_partition_taxes) {
            const tax_details = base_line.tax_details;
            const taxes_data = tax_details.taxes_data;

            if (!taxes_to_exclude.length) {
                base_lines_for_dp.push(
                    this.prepare_base_line_for_taxes_computation(base_line, {
                        price_unit:
                            base_line.price_unit *
                            base_line.quantity *
                            (1 - base_line.discount / 100.0),
                        quantity: 1.0,
                        discount: 0.0,
                        manual_tax_amounts: base_line.manual_tax_amounts,
                    })
                );
                continue;
            }

            // Split the taxes in multiple batch of taxes, one per sub base line.
            const new_taxes = [];
            const new_base_lines_for_dp = [];
            for (const tax_data of taxes_data) {
                const tax = tax_data.tax;
                if (taxes_to_keep.includes(tax)) {
                    new_taxes.push(tax);
                } else if (!tax.price_include) {
                    // The tax is standalone and can just be extracted as a fixed amount.
                    new_base_lines_for_dp.push(
                        this.prepare_base_line_for_taxes_computation(base_line, {
                            price_unit: tax_data.tax_amount_currency,
                            quantity: 1.0,
                            discount: 0.0,
                            tax_ids: tax_data.taxes.filter((t) => taxes_to_keep.includes(t)),
                        })
                    );
                } else {
                    continue;
                }
            }

            if (new_base_lines_for_dp.length > 0) {
                if (new_taxes.length > 0) {
                    const price_unit_after_discount =
                        base_line.price_unit * (1 - base_line.discount / 100.0);
                    new_base_lines_for_dp.push(
                        this.prepare_base_line_for_taxes_computation(base_line, {
                            price_unit: base_line.quantity * price_unit_after_discount,
                            quantity: 1.0,
                            discount: 0.0,
                            tax_ids: new_taxes,
                        })
                    );
                }
            } else {
                // The base line can be used as raw since it doesn't contain taxes to be excluded.
                const price_unit_after_discount =
                    base_line.price_unit * (1 - base_line.discount / 100.0);
                new_base_lines_for_dp.push(
                    this.prepare_base_line_for_taxes_computation(base_line, {
                        price_unit: base_line.quantity * price_unit_after_discount,
                        quantity: 1.0,
                        discount: 0.0,
                        tax_ids: new_taxes,
                    })
                );
            }
            base_lines_for_dp.push(...new_base_lines_for_dp);
        }
        this.add_tax_details_in_base_lines(base_lines_for_dp, company);
        this.round_base_lines_tax_details(base_lines_for_dp, company);
        return base_lines_for_dp;
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    prepare_down_payment_lines(
        base_lines,
        company,
        amount_type,
        amount,
        { computation_key = "down_payment", grouping_function = null } = {}
    ) {
        const base_lines_for_dp = this.prepare_base_lines_for_down_payment(base_lines, company);
        const new_base_lines = this.reduce_base_lines_to_target_amount(
            base_lines_for_dp,
            company,
            amount_type,
            amount,
            { computation_key: computation_key, grouping_function: grouping_function }
        );
        this.fix_base_lines_tax_details_on_manual_tax_amounts(new_base_lines, company);
        return new_base_lines;
    },
};
