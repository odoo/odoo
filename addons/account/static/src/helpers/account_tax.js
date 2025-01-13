import { roundPrecision } from "@web/core/utils/numbers";

export const accountTaxHelpers = {
    // -------------------------------------------------------------------------
    // HELPERS IN BOTH PYTHON/JAVASCRIPT (account_tax.js / account_tax.py)

    // PREPARE TAXES COMPUTATION
    // -------------------------------------------------------------------------

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    prepare_taxes_batches(taxes_data) {
        const batches = [];

        let current_batch = null;
        let is_base_affected = null;
        let index = 0;
        for (const tax_data of taxes_data.toReversed()) {
            is_base_affected = tax_data.is_base_affected;
            if (current_batch !== null) {
                const same_amount_type = tax_data.amount_type === current_batch.amount_type;
                const same_price_include = tax_data.price_include === current_batch.price_include;
                const same_incl_base_amount_not_affected =
                    tax_data.include_base_amount &&
                    tax_data.include_base_amount === current_batch.include_base_amount &&
                    (
                        !is_base_affected ||
                        (!current_batch.is_base_affected && index === taxes_data.length - 1)
                    );
                const same_inc_base_amount =
                    tax_data.include_base_amount === current_batch.include_base_amount &&
                    !tax_data.include_base_amount &&
                    is_base_affected === current_batch.is_base_affected;
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
                    is_base_affected: is_base_affected,
                };
            }

            current_batch.taxes.push(tax_data);
            ++index;
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

        return batches;
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
                if (!special_mode || special_mode === "total_included") {
                    if (!batch.include_base_amount) {
                        for (const other_batch of batches_after) {
                            if (other_batch._original_price_include) {
                                add_extra_base(other_batch, tax_data, -1);
                            }
                        }
                    }
                    for (const other_batch of batches_before) {
                        add_extra_base(other_batch, tax_data, -1);
                    }
                } else {  // special_mode === "total_excluded"
                    for (const other_batch of batches_after) {
                        if (!other_batch._original_price_include || batch.include_base_amount) {
                            add_extra_base(other_batch, tax_data, 1);
                        }
                    }
                }
            } else if (!batch._original_price_include) {
                if (!special_mode || special_mode === "total_excluded") {
                    if (batch.include_base_amount) {
                        for (const other_batch of batches_after) {
                            if (other_batch.is_base_affected) {
                                add_extra_base(other_batch, tax_data, 1);
                            }
                        }
                    }
                } else {  // special_mode === "total_included"
                    if (!batch.include_base_amount) {
                        for (const other_batch of batches_after) {
                            add_extra_base(other_batch, tax_data, -1);
                        }
                    }
                    for (const other_batch of batches_before) {
                        add_extra_base(other_batch, tax_data, -1);
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
            force_price_include = null,
            is_refund = false,
            include_caba_tags = false,
            special_mode = false,
        } = {}
    ) {
        // Backward-compatibility in stable version:
        if (!special_mode && force_price_include) {
            special_mode = "total_included";
        }

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

        // Group the taxes by batch of computation.
        const descending_batches = this.prepare_taxes_batches(expanded_taxes_data);
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
                        if (!next_tax_data.is_base_affected) {
                            continue;
                        }
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
        {
            rounding_method = "round_per_line",
            precision_rounding = null,
            reverse = false,
            round_price_include = true,
        } = {}
    ) {
        if (rounding_method === "round_globally" && !round_price_include) {
            precision_rounding = null;
        } else if (!precision_rounding) {
            precision_rounding = 0.01;
        }
        let raw_price = price_unit * quantity
        if (precision_rounding) {
            raw_price = roundPrecision(raw_price, precision_rounding);
        }
        return {
            product: product_values,
            price_unit: price_unit,
            raw_price: raw_price,
            quantity: quantity,
            rounding_method: rounding_method,
            precision_rounding: precision_rounding,
            round_price_include: round_price_include,
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

        let raw_base = evaluation_context.raw_price + evaluation_context.extra_base;
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
        const raw_base = evaluation_context.raw_price + evaluation_context.extra_base;

        if (price_include) {
            const base = special_mode === "total_excluded" ? raw_base : raw_base - total_tax_amount;
            if (amount_type === "division") {
                return {
                    base: base,
                    display_base: raw_base,
                };
            } else {
                return {
                    base: base,
                    display_base: base,
                };
            }
        }

        // Price excluded.
        return {
            base: raw_base,
            display_base: raw_base,
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
        const round_price_include = evaluation_context.round_price_include;
        let eval_taxes_data = taxes_data.map((tax_data) => Object.assign({}, tax_data));
        const skipped = new Set();
        for (const [quid, index] of eval_order_indexes) {
            const tax_data = eval_taxes_data[index];
            const special_mode = tax_data.evaluation_context.special_mode;
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
                if (tax_amount === undefined) {
                    skipped.add(tax_data.id);
                    tax_amount = 0.0;
                }
                tax_data.tax_amount = tax_amount;
                tax_data.tax_amount_factorized = tax_data.tax_amount * tax_data._factor;
                if (
                    rounding_method === "round_per_line" ||
                    ((special_mode === 'total_included' || (!special_mode && tax_data.price_include)) && round_price_include)
                ) {
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
                if (
                    rounding_method === "round_per_line" ||
                    ((special_mode === 'total_included' || (!special_mode && tax_data.price_include)) && round_price_include)
                ) {
                    tax_data.base = roundPrecision(tax_data.base, prec_rounding);
                    tax_data.display_base = roundPrecision(tax_data.display_base, prec_rounding);
                }
            }
        }

        if (skipped.length > 0) {
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
            total_excluded = total_included = evaluation_context.raw_price;
            if (rounding_method === "round_per_line") {
                total_excluded = total_included = roundPrecision(total_excluded, prec_rounding);
            }
        }

        return {
            taxes_data: eval_taxes_data,
            total_excluded: total_excluded,
            total_included: total_included,
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
            { rounding_method: "round_globally", round_price_include: false }
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
            { rounding_method: "round_globally", round_price_include: false }
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
    // PURE JS HELPERS
    // -------------------------------------------------------------------------

    computeSingleLineTaxes(
        taxes_data,
        evaluation_context,
        { force_price_include = false, is_refund = false, include_caba_tags = false } = {}
    ) {
        const taxes_computation = this.prepare_taxes_computation(taxes_data, {
            force_price_include: force_price_include,
            is_refund: is_refund,
            include_caba_tags: include_caba_tags,
        });
        return this.eval_taxes_computation(taxes_computation, evaluation_context);
    },
};
