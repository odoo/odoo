import { roundPrecision } from "@web/core/utils/numbers";
import { _t } from "@web/core/l10n/translation";

export const accountTaxHelpers = {
    // -------------------------------------------------------------------------
    // HELPERS IN BOTH PYTHON/JAVASCRIPT (account_tax.js / account_tax.py)

    // PREPARE TAXES COMPUTATION
    // -------------------------------------------------------------------------

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    prepare_taxes_batches(taxes_data, { special_mode = false } = {}) {
        // Flatten the taxes and order them.
        const sorted_taxes_data = taxes_data.sort(
            (v1, v2) => v1.sequence - v2.sequence || v1.id - v2.id
        );
        const flatten_taxes_data = [];
        for (const tax_data of sorted_taxes_data) {
            if (tax_data.amount_type === "group") {
                const sorted_children_tax_ids = tax_data._children_tax_ids.sort(
                    (v1, v2) => v1.sequence - v2.sequence || v1.id - v2.id
                );
                for (const child_tax_data of sorted_children_tax_ids) {
                    flatten_taxes_data.push(child_tax_data);
                }
            } else {
                flatten_taxes_data.push(tax_data);
            }
        }
        const expanded_taxes_data = [];
        for (let index = 0; index < flatten_taxes_data.length; index++) {
            const tax_data = flatten_taxes_data[index];
            let price_include;
            if (special_mode === "total_included") {
                price_include = true;
            } else if (special_mode === "total_excluded") {
                price_include = false;
            } else {
                price_include = tax_data.price_include;
            }
            expanded_taxes_data.push({
                ...tax_data,
                price_include: price_include,
                _original_price_include: tax_data.price_include,
                index: index,
                evaluation_context: { special_mode: special_mode },
            });
        }

        const batches = [];

        let current_batch = null;
        let is_base_affected = null;
        for (const tax_data of expanded_taxes_data.toReversed()) {
            if (current_batch !== null) {
                const same_amount_type = tax_data.amount_type === current_batch.amount_type;
                const same_price_include = tax_data.price_include === current_batch.price_include;
                const same_incl_base_amount_not_affected =
                    tax_data.include_base_amount &&
                    tax_data.include_base_amount === current_batch.include_base_amount &&
                    !is_base_affected;
                const same_inc_base_amount =
                    tax_data.include_base_amount === current_batch.include_base_amount &&
                    !tax_data.include_base_amount;
                const same_batch =
                    same_amount_type &&
                    same_price_include &&
                    (same_inc_base_amount || same_incl_base_amount_not_affected);
                if (!same_batch) {
                    batches.push(current_batch);
                    current_batch = null;
                }
            }

            if (current_batch === null) {
                current_batch = {
                    taxes: [],
                    extra_base_for_tax: [],
                    extra_base_for_base: [],
                    amount_type: tax_data.amount_type,
                    include_base_amount: tax_data.include_base_amount,
                    price_include: tax_data.price_include,
                    _original_price_include: tax_data._original_price_include,
                    is_tax_computed: false,
                    is_base_computed: false,
                };
            }

            is_base_affected = tax_data.is_base_affected;
            current_batch.taxes.push(tax_data);
        }

        if (current_batch !== null) {
            batches.push(current_batch);
        }

        for (let index = 0; index < batches.length; index++) {
            const batch = batches[index];
            const batch_indexes = batch.taxes.map((x) => x.index);
            batch.taxes = batch.taxes.toReversed();
            for (const tax_data of batch.taxes) {
                tax_data.batch_indexes = batch_indexes;
            }
            this.precompute_taxes_batch(batch);
        }

        return [ batches, expanded_taxes_data ];
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    precompute_taxes_batch(batch) {
        const taxes_data = batch.taxes;
        const amount_type = batch.amount_type;

        if (amount_type === "fixed") {
            for (const tax_data of taxes_data) {
                tax_data.evaluation_context.quantity_multiplicator =
                    tax_data.amount * tax_data._factor;
            }
        } else if (amount_type === "percent") {
            const total_percentage =
                taxes_data.reduce((acc, tax_data) => acc + tax_data.amount * tax_data._factor, 0) /
                100.0;
            for (const tax_data of taxes_data) {
                const percentage = tax_data.amount / 100.0;
                tax_data.evaluation_context.incl_base_multiplicator =
                    total_percentage !== -1 ? 1 / (1 + total_percentage) : 0.0;
                tax_data.evaluation_context.excl_tax_multiplicator = percentage;
            }
        } else if (amount_type === "division") {
            const total_percentage =
                taxes_data.reduce((acc, tax_data) => acc + tax_data.amount * tax_data._factor, 0) /
                100.0;
            const incl_base_multiplicator = (total_percentage === 1.0) ? 1.0 : 1 - total_percentage;
            for (const tax_data of taxes_data) {
                const percentage = tax_data.amount / 100.0;
                tax_data.evaluation_context.incl_base_multiplicator = incl_base_multiplicator;
                tax_data.evaluation_context.excl_tax_multiplicator = percentage / incl_base_multiplicator;
            }
        }
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    process_as_fixed_tax_amount_batch(batch) {
        return batch.amount_type === "fixed";
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    propagate_extra_taxes_base(
        batches_before,
        batch,
        batches_after,
        { special_mode = false } = {}
    ) {
        function add_extra_base(other_batch, tax_data, sign){
            if (!other_batch.tax_order_added) {
                other_batch.extra_base_for_tax.push([sign, tax_data.index]);
            }
            other_batch.extra_base_for_base.push([sign, tax_data.index]);
        }

        for (const tax_data of batch.taxes) {
            if (batch._original_price_include) {
                if (!special_mode) {
                    for (const other_batch of batches_before) {
                        add_extra_base(other_batch, tax_data, -1);
                    }
                } else if (special_mode === "total_excluded") {
                    for (const other_batch of batches_after) {
                        if (!other_batch.price_include) {
                            add_extra_base(other_batch, tax_data, 1);
                        }
                    }
                } else if (special_mode === "total_included") {
                    for (const other_batch of batches_before) {
                        add_extra_base(other_batch, tax_data, -1);
                    }
                }
            } else if (!batch._original_price_include) {
                if (!special_mode || special_mode === "total_excluded") {
                    if (batch.include_base_amount) {
                        for (const other_batch of batches_after) {
                            add_extra_base(other_batch, tax_data, 1);
                        }
                    }
                } else if (special_mode === "total_included") {
                    if (!batch.include_base_amount) {
                        for (const other_batch of batches_before.concat(batches_after)) {
                            add_extra_base(other_batch, tax_data, -1);
                        }
                    }
                }
            }
        }
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    prepare_taxes_computation(
        taxes_data,
        {
            is_refund = false,
            include_caba_tags = false,
            special_mode = false,
        } = {}
    ) {
        // Group the taxes by batch of computation.
        const [batches, expanded_taxes_data] = this.prepare_taxes_batches(taxes_data, { special_mode: special_mode });
        const descending_batches = batches;
        const ascending_batches = descending_batches.toReversed();
        const eval_order_indexes = [];

        // Define the order in which the taxes must be evaluated.
        // Fixed taxes are computed directly because they could affect the base of a price included batch right after.
        for (let i = 0; i < descending_batches.length; i++) {
            const batch = descending_batches[i];
            if (this.process_as_fixed_tax_amount_batch(batch)) {
                batch.tax_order_added = true;
                for (const tax_data of batch.taxes) {
                    eval_order_indexes.push(["tax", tax_data.index]);
                }
                this.propagate_extra_taxes_base(
                    descending_batches.slice(i + 1),
                    batch,
                    descending_batches.slice(0, i),
                    { special_mode: special_mode }
                );
            }
        }

        // Then, const's travel the batches in the reverse order and process the price-included taxes.
        for (let i = 0; i < descending_batches.length; i++) {
            const batch = descending_batches[i];
            if (!batch.tax_order_added && batch.price_include) {
                batch.tax_order_added = true;
                for (const tax_data of batch.taxes) {
                    eval_order_indexes.push(["tax", tax_data.index]);
                }
                this.propagate_extra_taxes_base(
                    descending_batches.slice(i + 1),
                    batch,
                    descending_batches.slice(0, i),
                    { special_mode: special_mode }
                );
            }
        }

        // Then, const's travel the batches in the normal order and process the price-excluded taxes.
        for (let i = 0; i < ascending_batches.length; i++) {
            const batch = ascending_batches[i];
            if (!batch.tax_order_added && !batch.price_include) {
                batch.tax_order_added = true;
                for (const tax_data of batch.taxes) {
                    eval_order_indexes.push(["tax", tax_data.index]);
                }
                this.propagate_extra_taxes_base(
                    ascending_batches.slice(0, i),
                    batch,
                    ascending_batches.slice(i + 1),
                    { special_mode: special_mode }
                );
            }
        }

        // Mark the base to be computed in the descending order. The order doesn't matter for no special mode or 'total_excluded' but
        // it must be in the reverse order when special_mode is 'total_included'.
        for (const batch of descending_batches) {
            for (const tax_data of batch.taxes) {
                eval_order_indexes.push(["base", tax_data.index]);
            }
        }

        // Compute the subsequent taxes / tags.
        for (let i = 0; i < ascending_batches.length; i++) {
            const batch = ascending_batches[i];
            const subsequent_tax_ids = [];
            const subsequent_tag_ids = new Set();
            const base_tags_field = is_refund ? "_refund_base_tag_ids" : "_invoice_base_tag_ids";
            if (batch.include_base_amount) {
                for (const next_batch of ascending_batches.toSpliced(0, i + 1)) {
                    for (const next_tax_data of next_batch.taxes) {
                        subsequent_tax_ids.push(next_tax_data.id);
                        if (include_caba_tags || next_tax_data.tax_exigibility !== "on_payment") {
                            for (const tag_id of next_tax_data[base_tags_field]) {
                                subsequent_tag_ids.add(tag_id);
                            }
                        }
                    }
                }
            }

            for (const tax_data of batch.taxes) {
                Object.assign(tax_data, {
                    tax_ids: subsequent_tax_ids,
                    tag_ids: [...subsequent_tag_ids],
                    extra_base_for_base: batch.extra_base_for_base,
                    extra_base_for_tax: batch.extra_base_for_tax,
                });
            }
        }

        return {
            taxes_data: expanded_taxes_data,
            eval_order_indexes: eval_order_indexes,
        };
    },

    // -------------------------------------------------------------------------
    // EVAL TAXES COMPUTATION
    // -------------------------------------------------------------------------

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    eval_taxes_computation_prepare_product_values(default_product_values, product) {
        const product_values = {};
        for (const [field_name, field_info] of Object.entries(default_product_values)) {
            product_values[field_name] = product
                ? product[field_name] || field_info.default_value
                : field_info.default_value;
        }
        return product_values;
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    eval_taxes_computation_prepare_context(
        price_unit,
        quantity,
        product_values,
        { rounding_method = "round_per_line", precision_rounding = 0.01 } = {}
    ) {
        return {
            product: product_values,
            price_unit: price_unit,
            quantity: quantity,
            rounding_method: rounding_method,
            precision_rounding: rounding_method === "round_globally" ? null : precision_rounding,
        };
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    eval_tax_amount(tax_data, evaluation_context) {
        const amount_type = tax_data.amount_type;
        const special_mode = tax_data.special_mode;
        const price_include = tax_data.price_include;

        if (amount_type === "fixed") {
            return evaluation_context.quantity * evaluation_context.quantity_multiplicator;
        }

        let raw_base =
            evaluation_context.quantity * evaluation_context.price_unit +
            evaluation_context.extra_base;
        if (
            "incl_base_multiplicator" in evaluation_context &&
            ((price_include && !special_mode) || special_mode === "total_included")
        ) {
            raw_base *= evaluation_context.incl_base_multiplicator;
        }

        if ("excl_tax_multiplicator" in evaluation_context) {
            return raw_base * evaluation_context.excl_tax_multiplicator;
        }
        return 0.0;
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    eval_tax_base_amount(tax_data, evaluation_context) {
        const price_include = tax_data.price_include;
        const amount_type = tax_data.amount_type;
        const total_tax_amount = evaluation_context.total_tax_amount;
        const special_mode = evaluation_context.special_mode;

        let raw_base =
            evaluation_context.quantity * evaluation_context.price_unit +
            evaluation_context.extra_base;
        if (price_include) {
            raw_base = special_mode === "total_excluded" ? raw_base : raw_base - total_tax_amount;
        }

        return {
            base: raw_base,
        };
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    eval_taxes_computation(taxes_computation, evaluation_context) {
        const taxes_data = taxes_computation.taxes_data;
        const eval_order_indexes = taxes_computation.eval_order_indexes;
        const rounding_method = evaluation_context.rounding_method;
        const prec_rounding = evaluation_context.precision_rounding;
        let eval_taxes_data = taxes_data.map((tax_data) => Object.assign({}, tax_data));
        const skipped = new Set();
        for (const [quid, index] of eval_order_indexes) {
            const tax_data = eval_taxes_data[index];
            if (quid === "tax") {
                let extra_base = 0.0;
                for (const [extra_base_sign, extra_base_index] of tax_data.extra_base_for_tax) {
                    extra_base +=
                        extra_base_sign * eval_taxes_data[extra_base_index].tax_amount_factorized;
                }
                let tax_amount = this.eval_tax_amount(tax_data, {
                    ...evaluation_context,
                    ...tax_data.evaluation_context,
                    extra_base: extra_base,
                });
                if (tax_amount === null) {
                    skipped.add(tax_data.id);
                    tax_amount = 0.0;
                }
                tax_data.tax_amount = tax_amount;
                tax_data.tax_amount_factorized = tax_data.tax_amount * tax_data._factor;
                if (rounding_method === "round_per_line") {
                    tax_data.tax_amount_factorized = roundPrecision(
                        tax_data.tax_amount_factorized,
                        prec_rounding
                    );
                }
            } else if (quid === "base") {
                let extra_base = 0.0;
                for (const [extra_base_sign, extra_base_index] of tax_data.extra_base_for_base) {
                    extra_base +=
                        extra_base_sign * eval_taxes_data[extra_base_index].tax_amount_factorized;
                }
                let total_tax_amount = 0.0;
                for (const batch_index of tax_data.batch_indexes) {
                    total_tax_amount += eval_taxes_data[batch_index].tax_amount_factorized;
                }
                Object.assign(
                    tax_data,
                    this.eval_tax_base_amount(tax_data, {
                        ...evaluation_context,
                        ...tax_data.evaluation_context,
                        extra_base: extra_base,
                        total_tax_amount: total_tax_amount,
                    })
                );
                if (rounding_method === "round_per_line") {
                    tax_data.base = roundPrecision(
                        tax_data.base,
                        prec_rounding
                    );
                }
            }
        }

        if (skipped.size > 0) {
            eval_taxes_data = eval_taxes_data.filter((tax_data) => !skipped.has(tax_data.id));
        }

        let total_excluded = null;
        let total_included = null;
        if (eval_taxes_data.length > 0) {
            total_excluded = eval_taxes_data[0].base;
            let tax_amount = 0.0;
            for (const tax_data of eval_taxes_data) {
                tax_amount += tax_data.tax_amount_factorized;
            }
            total_included = total_excluded + tax_amount;
        } else {
            total_excluded = total_included =
                evaluation_context.quantity * evaluation_context.price_unit;
            if (rounding_method === "round_per_line") {
                total_excluded = total_included = roundPrecision(total_excluded, prec_rounding);
            }
        }

        const tax_details = {};
        for(const tax_data of eval_taxes_data){
            tax_details[tax_data.id] = {
                tax_amount: tax_data.tax_amount_factorized,
                base_amount: tax_data.base,
            };
        }
        return {
            taxes_data: eval_taxes_data,
            total_excluded: total_excluded,
            total_included: total_included,
            tax_details: tax_details,
        };
    },

    // -------------------------------------------------------------------------
    // EVAL TAXES COMPUTATION
    // -------------------------------------------------------------------------

    adapt_price_unit_to_another_taxes(
        price_unit,
        product_values,
        original_taxes_data,
        new_taxes_data
    ) {
        const original_tax_ids = new Set(original_taxes_data.map((x) => x.id));
        const new_tax_ids = new Set(new_taxes_data.map((x) => x.id));
        if (
            (original_tax_ids.size === new_tax_ids.size &&
                [...original_tax_ids].every((value) => new_tax_ids.has(value))) ||
            original_taxes_data.some((x) => !x.price_include)
        ) {
            return price_unit;
        }

        let taxes_computation = this.prepare_taxes_computation(original_taxes_data);
        let evaluation_context = this.eval_taxes_computation_prepare_context(
            price_unit,
            1.0,
            product_values,
            { rounding_method: "round_globally" }
        );
        taxes_computation = this.eval_taxes_computation(taxes_computation, evaluation_context);
        price_unit = taxes_computation.total_excluded;

        taxes_computation = this.prepare_taxes_computation(new_taxes_data, {
            special_mode: "total_excluded",
        });
        evaluation_context = this.eval_taxes_computation_prepare_context(
            price_unit,
            1.0,
            product_values,
            { rounding_method: "round_globally" }
        );
        taxes_computation = this.eval_taxes_computation(taxes_computation, evaluation_context);
        let delta = 0.0;
        for (const tax_data of taxes_computation.taxes_data) {
            if (tax_data._original_price_include) {
                delta += tax_data.tax_amount_factorized;
            }
        }
        return price_unit + delta;
    },

    // -------------------------------------------------------------------------
    // GENERIC REPRESENTATION OF BUSINESS OBJECTS
    // -------------------------------------------------------------------------

    create_document_for_taxes_computation(currency, company) {
        return {
            currency: {
                id: currency.id,
                precision_rounding: currency.precision_rounding,
                precision_digits: Math.round(Math.abs(Math.log10(currency.precision_rounding))),
            },
            company: {
                currency_id: company.currency_id,
                precision_rounding: company.precision_rounding,
                precision_digits: Math.round(Math.abs(Math.log10(company.precision_rounding))),
                rounding_method: company.rounding_method,
            },
            lines: [],
        };
    },

    prepare_document_line(
        price_unit,
        quantity,
        discount,
        { product = null,  tax_details = null, taxes = null, rate = 1.0 } = {}
    ) {
        const discounted_price_unit = price_unit * (1 - discount / 100.0);
        const line = {
            price_unit: price_unit,
            discounted_price_unit: discounted_price_unit,
            quantity: quantity,
            discount: discount,
            product_values: product || {},
            taxes_data: taxes || [],
            rate: rate,
        };

        if (tax_details !== null) {
            line.tax_details = tax_details;
        }

        return line;
    },

    add_cash_rounding_to_document(
        document_values,
        cash_rounding,
    ) {
        document_values.cash_rounding = {
            strategy: cash_rounding.strategy,
            precision_rounding: cash_rounding.precision_rounding,
            rounding_method: cash_rounding.rounding_method,
        };
    },

    add_line_tax_amounts_to_document(document_values) {
        const currency_pr = document_values.currency.precision_rounding;
        const company_pr = document_values.company.precision_rounding;
        const rounding_method = document_values.company.rounding_method;
        for(const line of document_values.lines) {
            if (!("tax_details" in line)){
                const evaluation_context = this.eval_taxes_computation_prepare_context(
                    line.discounted_price_unit,
                    line.quantity,
                    line.product_values,
                    {
                        rounding_method: rounding_method,
                        precision_rounding: currency_pr,
                    }
                );

                const taxes_computation = this.eval_taxes_computation(
                    this.prepare_taxes_computation(line.taxes_data),
                    evaluation_context
                );
                line.tax_details = {};
                for(const [tax_id, amounts] of Object.entries(taxes_computation.tax_details)){
                    line.tax_details[tax_id] = {
                        tax_amount_currency: amounts.tax_amount,
                        tax_amount: amounts.tax_amount * line.rate,
                        base_amount_currency: amounts.base_amount,
                        base_amount: amounts.base_amount * line.rate,
                    }
                }
            }

            const tax_details = line.tax_details;
            let total_excluded_currency = null;
            let total_excluded = null;
            let total_included_currency = null;
            let total_included = null;
            if(Object.keys(tax_details).length > 0){
                const tax_details_values = Object.values(tax_details);
                const first = tax_details_values[0];
                total_excluded_currency = first.base_amount_currency;
                total_excluded = first.base_amount;
                tax_amount_currency = tax_details_values.reduce((acc, tax_data) => acc + tax_data.tax_amount_currency);
                tax_amount = tax_details_values.reduce((acc, tax_data) => acc + tax_data.tax_amount);
                total_included_currency = total_excluded_currency + tax_amount_currency;
                total_included = total_excluded + tax_amount;
            }else{
                total_excluded_currency = total_included_currency = line.quantity * line.discounted_price_unit;
                total_excluded = total_included = line.quantity * line.discounted_price_unit * line.rate;
            }
            line.total_excluded_currency = roundPrecision(total_excluded_currency, currency_pr);
            line.total_excluded = roundPrecision(total_excluded, company_pr);
            line.total_included_currency = roundPrecision(total_included_currency, currency_pr);
            line.total_included = roundPrecision(total_included, company_pr);
        }
    },

    // -------------------------------------------------------------------------
    // DISCOUNT
    // -------------------------------------------------------------------------

    prepare_document_global_discount_percentage_line(document_values, line, factor_percent) {
        const total_included = line.total_included;
        const new_taxes_data = line.taxes_data.filter(x => x._is_discountable);
        const evaluation_context = this.eval_taxes_computation_prepare_context(
            -factor_percent * total_included,
            1.0,
            line.product_values,
            { rounding_method: "round_globally" }
        );

        const taxes_computation = this.eval_taxes_computation(
            this.prepare_taxes_computation(line.taxes_data, { special_mode: "total_included" }),
            evaluation_context
        );

        return this.prepare_document_line({
            price_unit: taxes_computation.total_excluded,
            quantity: 1.0,
            discount: 0.0,
            taxes: new_taxes_data,
            tax_details: taxes_computation.tax_details
        });
    },

    // -------------------------------------------------------------------------
    // TAXES AGGREGATOR
    // -------------------------------------------------------------------------

    add_batch_display_base(batch) {
        const amount_type = batch.amount_type;
        if (amount_type === "fixed") {
            for(const tax_data of batch.taxes) {
                tax_data.display_base = null;
                tax_data.display_base_type = "none";
            }
        }else if(amount_type === "division" && batch.price_include) {
            let display_base = 0.0;
            for(const tax_data of batch.taxes) {
                display_base += tax_data.tax_amount;
            }
            for(const tax_data of batch.taxes) {
                tax_data.display_base = tax_data.base + display_base;
                tax_data.display_base_type = "total_included";
            }
        }else{
            for(const tax_data of batch.taxes) {
                tax_data.display_base = tax_data.base;
                tax_data.display_base_type = "same_base";
            }
        }
    },

    aggregate_display_bases(display_bases) {
        const display_bases_per_type = {};
        for (const [display_base, base, display_base_type] of display_bases) {
            if (!(display_base_type in display_bases_per_type)) {
                display_bases_per_type[display_base_type] = {
                    display_base_type: display_base_type,
                    display_base: display_base,
                    display_base_sum: null,
                    base: base,
                    base_sum: 0.0,
                };
            }
            const group = display_bases_per_type[display_base_type];
            group.base_sum += base;
            if (display_base !== null) {
                if (group.display_base_sum === null) {
                    group.display_base_sum = 0.0;
                }
                group.display_base_sum += display_base;
            }
        }

        if ("same_base" in display_bases_per_type) {
            display_bases_per_type.same_base.display_base = display_bases_per_type.same_base.base;
            display_bases_per_type.same_base.display_base_sum = display_bases_per_type.same_base.base_sum;
        }

        // All have the same display type.
        const first = Object.values(display_bases_per_type)[0];
        if (Object.keys(display_bases_per_type).length === 1) {
            return first;
        }

        // Mixed display_base_types.
        return {
            display_base: first.base,
            display_base_sum: first.base_sum,
            base: first.base,
            base_sum: first.base_sum,
            display_base_type: "same_base",
        };
    },

    aggregate_document_taxes(document_values, { grouping_key_function = null, aggregate_function = null } = {}) {

        function default_grouping_key_function(line, tax_data) {
            return { id: tax_data.id };
        }

        grouping_key_function = grouping_key_function || default_grouping_key_function;
        const currency_pr = document_values.currency.precision_rounding;
        const company_pr = document_values.company.precision_rounding;

        const results = {
            base_amount_currency: 0.0,
            base_amount: 0.0,
            tax_amount_currency: 0.0,
            tax_amount: 0.0,
            subtotals: {},
        };
        const subtotals = results.subtotals;

        const amounts_per_tax = {};
        const subtotals_per_line = {};
        const subtotals_per_line_grouping_key_order = {};
        document_values.lines.forEach((line, i) => {
            const tax_details = line.tax_details;

            const [batches, taxes_data] = this.prepare_taxes_batches(line.taxes_data);

            // Add the 'display_base_amount_currency'/'display_base_amount' because there are not part of the 'tax_details' per line.
            for(const batch of batches){
                for(const tax_data of batch.taxes){
                    Object.assign(tax_data, tax_details[tax_data.id]);
                }
                this.add_batch_display_base(batch);
            }

            // Untaxed amount.
            if(!Object.keys(taxes_data).length){
                results.base_amount_currency += roundPrecision(
                    line.quantity * line.discounted_price_unit,
                    currency_pr
                )
                results.base_amount += roundPrecision(
                    results.base_amount_currency * line.rate,
                    company_pr
                )
            }

            const encountered_grouping_keys = new Set();
            taxes_data.forEach(tax_data => {
                tax_data = Object.assign(tax_data, tax_details[tax_data.id]);

                const grouping_key_dict = grouping_key_function(line, tax_data);
                const grouping_key = JSON.stringify(grouping_key_dict);
                if (!(grouping_key in subtotals)) {
                    subtotals[grouping_key] = {
                        ...grouping_key_dict,
                        tax_amount_currency: 0.0,
                        tax_amount: 0.0,
                        base_amount_currency: 0.0,
                        base_amount: 0.0,
                        display_base: {},
                    };
                    if (aggregate_function) {
                        aggregate_function(line, tax_data, subtotals[grouping_key]);
                    }
                }
                const subtotal = subtotals[grouping_key];

                // Track the index of the line to retrieve it later.
                amounts_per_tax[tax_data.id].lines[i].index = i;

                // Register the grouping key now to keep them ordered per line.
                if (!(i in subtotals_per_line)) {
                    subtotals_per_line[i] = {};
                }
                if (!(grouping_key in subtotals_per_line[i])) {
                    subtotals_per_line[i][grouping_key] = {
                        ...grouping_key_dict,
                        raw_tax_amount_currency: 0.0,
                        raw_tax_amount: 0.0,
                        tax_amount_currency: 0.0,
                        tax_amount: 0.0,
                        raw_base_amount_currency: 0.0,
                        raw_base_amount: 0.0,
                        base_amount_currency: 0.0,
                        base_amount: 0.0,
                    };
                }

                // Register the grouping key now to keep them ordered per line.
                if (!(i in subtotals_per_line_grouping_key_order)) {
                    subtotals_per_line_grouping_key_order[i] = [];
                }
                if (!subtotals_per_line_grouping_key_order[i].includes(grouping_key)) {
                    subtotals_per_line_grouping_key_order[i].push(grouping_key);
                }
                if (!(i in subtotals_per_line)) {
                    subtotals_per_line[i] = {};
                }
                if (!(grouping_key in subtotals_per_line[i])) {
                    subtotals_per_line[i][grouping_key] = {
                        ...grouping_key_dict,
                        raw_tax_amount_currency: 0.0,
                        raw_tax_amount: 0.0,
                        tax_amount_currency: 0.0,
                        tax_amount: 0.0,
                        raw_base_amount_currency: 0.0,
                        raw_base_amount: 0.0,
                        base_amount_currency: 0.0,
                        base_amount: 0.0,
                    };
                }

                // Track the tax amount per tax.
                // We can't sum everything right now because we have to deal with the rounding at the end.
                // We need the 1) total per tax, 2) which part of each line is sum in this total and 3) the distribution accross the
                // grouping keys.
                amounts_per_tax[tax_data.id].tax_amount_currency += Math.abs(tax_data.tax_amount_currency);
                amounts_per_tax[tax_data.id].tax_amount += Math.abs(tax_data.tax_amount);
                amounts_per_tax[tax_data.id].lines[i].tax_amount_currency += tax_data.tax_amount_currency;
                amounts_per_tax[tax_data.id].lines[i].tax_amount += tax_data.tax_amount;
                amounts_per_tax[tax_data.id].lines[i].tax_grouping_keys.add(grouping_key);

                // Track the base amount.
                amounts_per_tax[tax_data.id].base_amount_currency += Math.abs(tax_data.base_amount_currency);
                amounts_per_tax[tax_data.id].base_amount += Math.abs(tax_data.base_amount);
                amounts_per_tax[tax_data.id].lines[i].base_amount_currency += tax_data.base_amount_currency;
                amounts_per_tax[tax_data.id].lines[i].base_amount += tax_data.base_amount;
                if (!encountered_grouping_keys.has(grouping_key)) {
                    encountered_grouping_keys.add(grouping_key);
                    amounts_per_tax[tax_data.id].lines[i].base_grouping_keys.add(grouping_key);
                }

                // Track the display_base amount.
                if (!(i in subtotal.display_base)) {
                    subtotal.display_base[i] = [];
                }
                subtotal.display_base[i].push([
                    tax_data.display_base_amount_currency,
                    tax_data.display_base,
                    tax_data.base_amount_currency,
                    tax_data.base_amount,
                    tax_data.display_base_type,
                ]);
            });
        });

        // Process 'tax_amount'.
        const accounted_line_indexes = new Set();
        for (const [grouping_key, total] of Object.entries(amounts_per_tax)) {
            const total_amount_currency = roundPrecision(
                total.base_amount_currency + total.tax_amount_currency,
                currency_pr
            );
            const total_amount = roundPrecision(
                total.base_amount + total.tax_amount,
                company_pr
            );
            const total_rounded_tax_amount_currency = roundPrecision(
                total.tax_amount_currency,
                currency_pr
            );
            total.tax_amount_currency = total_rounded_tax_amount_currency;
            const total_rounded_tax_amount = roundPrecision(
                total.tax_amount,
                company_pr
            );
            total.tax_amount = total_rounded_tax_amount;
            const total_rounded_base_amount_currency = roundPrecision(
                total_amount_currency - total.tax_amount_currency,
                currency_pr
            );
            total.base_amount_currency = total_rounded_base_amount_currency;
            const total_rounded_base_amount = roundPrecision(
                total_amount - total.tax_amount,
                company_pr
            );
            total.base_amount = total_rounded_base_amount;

            let i = 0;
            for (const line_total of Object.values(total.lines)) {
                const is_last_line = i === Object.keys(total.lines).length - 1;
                let line_rounded_tax_amount_currency = null;
                let line_rounded_tax_amount = null;
                let line_rounded_base_amount_currency = null;
                let line_rounded_base_amount = null;
                if (is_last_line) {
                    let sign = line_total.tax_amount_currency > 0.0 ? 1 : -1;
                    line_rounded_tax_amount_currency = sign * total_rounded_tax_amount_currency;
                    let sign = line_total.tax_amount > 0.0 ? 1 : -1;
                    line_rounded_tax_amount = sign * total_rounded_tax_amount;
                    sign = line_total.base_amount_currency > 0.0 ? 1 : -1;
                    line_rounded_base_amount_currency = sign * total_rounded_base_amount_currency;
                    sign = line_total.base_amount > 0.0 ? 1 : -1;
                    line_rounded_base_amount = sign * total_rounded_base_amount;
                } else {
                    line_rounded_tax_amount_currency = roundPrecision(
                        line_total.tax_amount_currency,
                        precision_rounding
                    );
                    line_rounded_tax_amount = roundPrecision(
                        line_total.tax_amount,
                        precision_rounding
                    );
                    line_rounded_base_amount_currency = roundPrecision(
                        line_total.base_amount_currency,
                        precision_rounding
                    );
                    line_rounded_base_amount = roundPrecision(
                        line_total.base_amount,
                        precision_rounding
                    );
                }
                const index = line_total.index;
                line_rounded_tax_amount_currency -= Math.abs(line_rounded_tax_amount_currency);
                total_rounded_tax_amount -= Math.abs(line_rounded_tax_amount);
                total_rounded_base_amount_currency -= Math.abs(line_rounded_base_amount_currency);
                total_rounded_base_amount -= Math.abs(line_rounded_base_amount);
                line_total.raw_tax_amount_currency = line_total.tax_amount_currency;
                line_total.raw_tax_amount = line_total.tax_amount;
                line_total.tax_amount_currency = line_rounded_tax_amount_currency;
                line_total.tax_amount = line_rounded_tax_amount;
                line_total.raw_base_amount_currency = line_total.base_amount_currency;
                line_total.raw_base_amount = line_total.base_amount;
                line_total.base_amount_currency = line_rounded_base_amount_currency;
                line_total.base_amount = line_rounded_base_amount;
                if(!accounted_line_indexes.has(index)){
                    const line = document_values.lines[index];
                    results.base_amount_currency += roundPrecision(line.total_excluded_currency, currency_pr);
                    results.base_amount += roundPrecision(line.total_excluded, company_pr);
                    accounted_line_indexes.add(index);
                }

                // TODO: TO BE CONTINUED.....
                // Dispatch per grouping_key.
                for (const grouping_key of line_total.tax_grouping_keys) {
                    subtotals[grouping_key].tax_amount += line_total.tax_amount;
                    const results_per_line = subtotals_per_line[index][grouping_key];
                    results_per_line.tax_amount += line_total.tax_amount;
                    results_per_line.raw_tax_amount += line_total.raw_tax_amount;
                }
                for (const grouping_key of line_total.base_grouping_keys) {
                    subtotals[grouping_key].base += line_total.base;
                    const results_per_line = subtotals_per_line[index][grouping_key];
                    results_per_line.base += line_total.base;
                    results_per_line.raw_base += line_total.raw_base;
                }
                i += 1;
            }
        }

        // Process 'display_base'.
        for (const subtotal of Object.values(subtotals)) {
            const display_bases = [];
            for (const line_display_bases of Object.values(subtotal.display_base)) {
                const aggregated_line_display_base = this.aggregate_display_bases(line_display_bases);
                display_bases.push([
                    aggregated_line_display_base.display_base,
                    aggregated_line_display_base.base,
                    aggregated_line_display_base.display_base_type,
                ]);
            }

            const aggregated_display_base = this.aggregate_display_bases(display_bases);
            subtotal.display_base = aggregated_display_base.display_base_sum;
            subtotal.display_base_type = aggregated_display_base.display_base_type;
            if (subtotal.display_base !== null){
                if (subtotal.display_base_type === "same_base"){
                    subtotal.display_base = subtotal.base;
                }else {
                    subtotal.display_base = roundPrecision(
                        subtotal.display_base,
                        precision_rounding
                    );
                }
            }
        }

        results.tax_amount = 0.0;

        // Process 'base'.
        for (const subtotal of Object.values(subtotals)) {
            results.tax_amount += subtotal.tax_amount;
        }

        // Total amounts.
        results.total_amount = results.untaxed_amount + results.tax_amount;

        // Totals per line.
        results.subtotals_per_line = {};
        for (const [line_index, totals] of Object.entries(subtotals_per_line)) {
            const line_grouping_key_order = subtotals_per_line_grouping_key_order[line_index];
            results.subtotals_per_line[line_index] = Object.entries(totals).sort((total1, total2) => {
                return line_grouping_key_order.indexOf(total1[0]) - line_grouping_key_order.indexOf(total2[0]);
            }).map(item => item[1]);
        }

        return results;
    },

    get_total_per_tax_summary(document_values) {
        function grouping_key_function(line, tax_data) {
            return { id: tax_data.id };
        }

        function aggregate_function(line, tax_data, results) {
            if (!("tax_data" in results)) {
                results.tax_data = tax_data;
            }
        }

        const aggregated_results = this.aggregate_document_taxes(
            document_values,
            { grouping_key_function: grouping_key_function, aggregate_function: aggregate_function }
        );

        const subtotals = {};
        for (const tax_amounts of Object.values(aggregated_results.subtotals)) {
            subtotals[tax_amounts.tax_data.id] = {
                tax_amount: tax_amounts.tax_amount,
                base: tax_amounts.base,
                display_base: tax_amounts.display_base,
            };
        }

        return {
            untaxed_amount: aggregated_results.untaxed_amount,
            tax_amount: aggregated_results.tax_amount,
            total_amount: aggregated_results.total_amount,
            subtotals: subtotals,
        };
    },

    // -------------------------------------------------------------------------
    // TAX TOTALS SUMMARY
    // -------------------------------------------------------------------------

    get_tax_totals_summary(document_values) {
        function grouping_key_function(line, tax_data) {
            return { tax_group_id: tax_data._tax_group.id };
        }

        function aggregate_function(line, tax_data, results) {
            if (!("tax_group" in results)) {
                const tax_group_values = tax_data._tax_group;
                results.tax_group = tax_group_values;
                results.order = [tax_group_values.sequence, tax_group_values.id];
            }
        }

        const aggregated_results = this.aggregate_document_taxes(
            document_values,
            { grouping_key_function: grouping_key_function, aggregate_function: aggregate_function }
        );

        const untaxed_amount_subtotal_label = _t("Untaxed Amount");
        const subtotals = {};
        const subtotals_order = {};
        const total_per_tax_group = Object.values(aggregated_results.subtotals).sort((group1, group2) => {
            return group1.order[0] - group2.order[0] || group1.order[1] - group2.order[1];
        });

        const encountered_base_amounts = new Set();
        for (let i = 0; i < total_per_tax_group.length; i++) {
            const total_values = total_per_tax_group[i];
            const tax_group_values = total_values.tax_group;
            const preceding_subtotal = tax_group_values.preceding_subtotal || untaxed_amount_subtotal_label;

            if (!(preceding_subtotal in subtotals_order)) {
                subtotals_order[preceding_subtotal] = total_values.order;
            }

            const subtotal = subtotals[preceding_subtotal] || {
                tax_groups: [],
                tax_amount: 0.0,
            };

            const tax_group = {
                id: total_values.tax_group.id,
                tax_amount: total_values.tax_amount,
                base: total_values.base,
                display_base: total_values.display_base,
                group_name: total_values.tax_group.name,
            };

            subtotal.tax_groups.push(tax_group);
            subtotal.tax_amount += total_values.tax_amount;

            if (total_values.display_base !== null) {
                encountered_base_amounts.add(parseFloat(total_values.display_base));
            }

            subtotals[preceding_subtotal] = subtotal;
        }

        if (Object.keys(subtotals).length === 0) {
            subtotals[untaxed_amount_subtotal_label] = {
                tax_groups: [],
                tax_amount: 0.0,
            };
        }

        const tax_totals_summary = {
            currency_id: document_values.currency.id,
            subtotals: [],
            untaxed_amount: aggregated_results.untaxed_amount,
            tax_amount: 0.0,
        };

        let cumulated_tax_amount = aggregated_results.untaxed_amount;
        const ordered_subtotals = Object.entries(subtotals).sort((group1, group2) => {
            return subtotals_order[group1[0]] - subtotals_order[group2[0]];
        });

        for (const [subtotal_label, subtotal] of ordered_subtotals) {
            subtotal.name = subtotal_label;
            subtotal.base = cumulated_tax_amount;
            tax_totals_summary.subtotals.push(subtotal);
            tax_totals_summary.tax_amount += subtotal.tax_amount;
            cumulated_tax_amount += subtotal.tax_amount;
        }

        tax_totals_summary.same_tax_base = encountered_base_amounts.size === 1;
        tax_totals_summary.total_amount = tax_totals_summary.untaxed_amount + tax_totals_summary.tax_amount;

        return tax_totals_summary;
    },

    apply_cash_rounding_to_tax_totals_summary(document_values, tax_totals_summary) {
        // Cash rounding.
        if (!document_values.cash_rounding) {
            return;
        }

        const precision_rounding = document_values.currency.precision_rounding;
        const cash_rounding_values = document_values.cash_rounding;
        const expected_total = roundPrecision(
            tax_totals_summary.total_amount,
            cash_rounding_values.precision_rounding,
            cash_rounding_values.rounding_method
        );

        const difference = roundPrecision(
            expected_total - tax_totals_summary.total_amount,
            precision_rounding
        );

        if (roundPrecision(difference, precision_rounding) !== 0.0) {
            const strategy = cash_rounding_values.strategy;

            if (strategy === "add_invoice_line") {
                tax_totals_summary.cash_rounding_amount = difference;
                tax_totals_summary.untaxed_amount += difference;
                tax_totals_summary.total_amount += difference;
            } else if (strategy === "biggest_tax") {
                let max_subtotal = null;
                let max_tax_group = null;
                let max_tax_amount = 0;

                for (const subtotal of tax_totals_summary.subtotals) {
                    for (const tax_group of subtotal.tax_groups) {
                        if (tax_group.tax_amount > max_tax_amount) {
                            max_subtotal = subtotal;
                            max_tax_group = tax_group;
                            max_tax_amount = tax_group.tax_amount;
                        }
                    }
                }

                if (max_tax_group) {
                    max_tax_group.cash_rounding_amount = difference;
                    max_tax_group.tax_amount += difference;
                    max_subtotal.tax_amount += difference;
                    tax_totals_summary.tax_amount += difference;
                    tax_totals_summary.total_amount += difference;
                }
            }
        }
    },

    exclude_tax_group_from_tax_totals_summary(tax_totals_summary, ids_to_exclude) {
        let ids_to_exclude_set = new Set(ids_to_exclude);

        let subtotals = [];
        for (let subtotal of tax_totals_summary.subtotals) {
            let tax_groups = [];
            for (let tax_group of subtotal.tax_groups) {
                if (ids_to_exclude_set.has(tax_group.id)) {
                    subtotal.base += tax_group.tax_amount;
                    subtotal.tax_amount -= tax_group.tax_amount;
                    tax_totals_summary.untaxed_amount += tax_group.tax_amount;
                    tax_totals_summary.tax_amount -= tax_group.tax_amount;
                } else {
                    tax_groups.push(tax_group);
                }
            }

            if (tax_groups.length > 0) {
                subtotal.tax_groups = tax_groups;
                subtotals.push(subtotal);
            }
        }

        tax_totals_summary.subtotals = subtotals;
    },

};
