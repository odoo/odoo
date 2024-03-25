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
    prepare_taxes_batches(tax_values_list) {
        const batches = [];

        let current_batch = null;
        let is_base_affected = null;
        for (const tax_values of tax_values_list.toReversed()) {
            if (current_batch !== null) {
                const same_amount_type = tax_values.amount_type === current_batch.amount_type;
                const same_price_include = tax_values.price_include === current_batch.price_include;
                const same_incl_base_amount_not_affected =
                    tax_values.include_base_amount &&
                    tax_values.include_base_amount === current_batch.include_base_amount &&
                    !is_base_affected;
                const same_inc_base_amount =
                    tax_values.include_base_amount === current_batch.include_base_amount &&
                    !tax_values.include_base_amount;
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
                    amount_type: tax_values.amount_type,
                    include_base_amount: tax_values.include_base_amount,
                    price_include: tax_values.price_include,
                };
            }

            is_base_affected = tax_values.is_base_affected;
            current_batch.taxes.push(tax_values);
        }

        if (current_batch !== null) {
            batches.push(current_batch);
        }

        for (const batch of batches) {
            const batch_indexes = batch.taxes.map((x) => x.index);
            batch.taxes = batch.taxes.toReversed();
            for (const tax_values of batch.taxes) {
                tax_values.batch_indexes = batch_indexes;
            }
        }

        return batches;
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    ascending_process_fixed_taxes_batch(batch) {
        if (batch.amount_type === "fixed") {
            batch.computed = "tax";
            for (const tax_values of batch.taxes) {
                tax_values.evaluation_context.quantity_multiplicator =
                    tax_values.amount * tax_values._factor;
            }
        }
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    descending_process_price_included_taxes_batch(batch) {
        const amount_type = batch.amount_type;
        const price_include = batch.price_include;

        if (!price_include) {
            return;
        }

        if (amount_type === "percent") {
            batch.computed = true;

            let total_reverse_percentage = 0.0;
            for (const tax_values of batch.taxes) {
                total_reverse_percentage += (tax_values.amount * tax_values._factor) / 100.0;
            }
            for (const tax_values of batch.taxes) {
                const percentage = tax_values.amount / 100.0;
                tax_values.evaluation_context.reverse_multiplicator = 1 + total_reverse_percentage;
                tax_values.evaluation_context.multiplicator =
                    percentage / (1 + total_reverse_percentage);
            }
        } else if (amount_type === "division") {
            batch.computed = true;

            let total_reverse_percentage = 0.0;
            for (const tax_values of batch.taxes) {
                total_reverse_percentage += (tax_values.amount * tax_values._factor) / 100.0;
            }
            for (const tax_values of batch.taxes) {
                const percentage = tax_values.amount / 100.0;
                tax_values.evaluation_context.reverse_multiplicator =
                    total_reverse_percentage === 1 ? 0.0 : 1 / (1 - total_reverse_percentage);
                tax_values.evaluation_context.multiplicator = percentage;
            }
        } else if (amount_type === "fixed") {
            batch.computed = true;
        }
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    ascending_process_taxes_batch(batch) {
        const amount_type = batch.amount_type;
        const price_include = batch.price_include;

        if (price_include) {
            return;
        }

        if (amount_type === "percent") {
            batch.computed = true;
            for (const tax_values of batch.taxes) {
                tax_values.evaluation_context.multiplicator = tax_values.amount / 100.0;
            }
        } else if (amount_type === "division") {
            batch.computed = true;

            let total_percentage = 0.0;
            for (const tax_values of batch.taxes) {
                total_percentage += (tax_values.amount * tax_values._factor) / 100.0;
            }
            for (const tax_values of batch.taxes) {
                const percentage = tax_values.amount / 100.0;
                const reverse_multiplicator =
                    total_percentage === 1 ? 0.0 : 1 / (1 - total_percentage);
                tax_values.evaluation_context.multiplicator = reverse_multiplicator * percentage;
            }
        } else if (amount_type === "fixed") {
            batch.computed = true;
        }
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    prepare_taxes_computation(
        tax_values_list,
        { force_price_include = null, is_refund = false, include_caba_tags = false } = {}
    ) {
        // Flatten the taxes and order them.
        const sorted_tax_values_list = tax_values_list.sort(
            (v1, v2) => v1.sequence - v2.sequence || v1.id - v2.id
        );
        let flatten_tax_values_list = [];
        for (const tax_values of sorted_tax_values_list) {
            if (tax_values.amount_type === "group") {
                const sorted_children_tax_ids = tax_values._children_tax_ids.sort(
                    (v1, v2) => v1.sequence - v2.sequence || v1.id - v2.id
                );
                for (const child_tax_values of sorted_children_tax_ids) {
                    flatten_tax_values_list.push(child_tax_values);
                }
            } else {
                flatten_tax_values_list.push(tax_values);
            }
        }
        flatten_tax_values_list = flatten_tax_values_list.map((tax_values, index) =>
            Object.assign(
                {
                    price_include:
                        force_price_include === null
                            ? tax_values.price_include
                            : force_price_include,
                    index: index,
                    evaluation_context: {},
                },
                tax_values
            )
        );

        // Group the taxes by batch of computation.
        const descending_batches = this.prepare_taxes_batches(flatten_tax_values_list);
        const ascending_batches = descending_batches.toReversed();

        // First ascending computation for fixed tax.
        // In Belgium, we have a fixed price-excluded tax that affects the base of a 21% price-included tax.
        // In that case, we need to compute the fix amount before the descending computation.
        const eval_order_indexes = [];
        const ascending_extra_base = [];
        for (const batch of ascending_batches) {
            batch.ascending_extra_base = [...ascending_extra_base];

            this.ascending_process_fixed_taxes_batch(batch);

            // Build the expression representing the extra base as a sum.
            if (
                [true, "tax"].includes(batch.computed) &&
                batch.include_base_amount &&
                !batch.price_include
            ) {
                for (const tax_values of batch.taxes) {
                    ascending_extra_base.push([1, tax_values.index]);
                }
            }

            if ([true, "tax"].includes(batch.computed)) {
                for (const tax_values of batch.taxes) {
                    eval_order_indexes.push(["tax", tax_values.index]);
                }
            }
            if (batch.computed === true) {
                for (const tax_values of batch.taxes) {
                    eval_order_indexes.push(["base", tax_values.index]);
                }
            }
        }

        // First descending computation to compute price_included values.
        const descending_extra_base = [];
        for (const batch of descending_batches) {
            const computed = batch.computed;
            batch.descending_extra_base = [...descending_extra_base];

            // Build the expression representing the extra base as a sum.
            if (!computed || computed === "tax") {
                batch.extra_base_for_base = descending_extra_base.concat(
                    batch.ascending_extra_base
                );
                batch.extra_base_for_tax = computed === "tax" ? [] : batch.extra_base_for_base;

                // Compute price-included taxes.
                this.descending_process_price_included_taxes_batch(batch);

                if (batch.computed === true) {
                    for (const tax_values of batch.taxes) {
                        descending_extra_base.push([-1, tax_values.index]);
                    }
                }

                if (batch.computed === true && computed !== "tax") {
                    for (const tax_values of batch.taxes) {
                        eval_order_indexes.push(["tax", tax_values.index]);
                    }
                }
                if (batch.computed === true) {
                    for (const tax_values of batch.taxes) {
                        eval_order_indexes.push(["base", tax_values.index]);
                    }
                }
            }
        }

        // Second ascending computation to compute the missing values for price-excluded taxes.
        // Build the final results.
        const extra_base = [];
        for (const [i, batch] of ascending_batches.entries()) {
            const computed = batch.computed;
            if (computed !== true) {
                // Build the expression representing the extra base as a sum.
                batch.extra_base_for_base = extra_base.concat(
                    batch.ascending_extra_base,
                    batch.descending_extra_base
                );
                batch.extra_base_for_tax = computed === "tax" ? [] : batch.extra_base_for_base;

                // Compute price-excluded taxes.
                this.ascending_process_taxes_batch(batch);

                // Update the base expression for the following taxes.
                if (!computed && batch.include_base_amount) {
                    for (const tax_values of batch.taxes) {
                        extra_base.push([1, tax_values.index]);
                    }
                }

                if (batch.computed === true && computed !== "tax") {
                    for (const tax_values of batch.taxes) {
                        eval_order_indexes.push(["tax", tax_values.index]);
                    }
                }
                if (batch.computed === true) {
                    for (const tax_values of batch.taxes) {
                        eval_order_indexes.push(["base", tax_values.index]);
                    }
                }
            }

            // Compute the subsequent taxes / tags.
            const subsequent_tax_ids = [];
            const subsequent_tag_ids = new Set();
            const base_tags_field = is_refund ? "_refund_base_tag_ids" : "_invoice_base_tag_ids";
            if (batch.include_base_amount) {
                for (const next_batch of ascending_batches.toSpliced(0, i + 1)) {
                    for (const next_tax_values of next_batch.taxes) {
                        subsequent_tax_ids.push(next_tax_values.id);
                        if (include_caba_tags || next_tax_values.tax_exigibility !== "on_payment") {
                            for (const tag_id of next_tax_values[base_tags_field]) {
                                subsequent_tag_ids.add(tag_id);
                            }
                        }
                    }
                }
            }

            for (const tax_values of batch.taxes) {
                Object.assign(tax_values, {
                    tax_ids: subsequent_tax_ids,
                    tag_ids: [...subsequent_tag_ids],
                    extra_base_for_base: batch.extra_base_for_base,
                    extra_base_for_tax: batch.extra_base_for_tax,
                });
            }
        }

        return {
            tax_values_list: flatten_tax_values_list,
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
        { rounding_method = "round_per_line", precision_rounding = 0.01, reverse = false } = {}
    ) {
        return {
            product: product_values,
            price_unit: price_unit,
            quantity: quantity,
            rounding_method: rounding_method,
            precision_rounding: rounding_method == "round_globally" ? null : precision_rounding,
            reverse: reverse,
        };
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    eval_tax_amount(tax_values, evaluation_context) {
        const amount_type = tax_values.amount_type;
        const reverse = evaluation_context.reverse;
        if (amount_type === "fixed") {
            return evaluation_context.quantity * evaluation_context.quantity_multiplicator;
        }
        let raw_base =
            evaluation_context.quantity * evaluation_context.price_unit +
            evaluation_context.extra_base;
        if (reverse && "reverse_multiplicator" in evaluation_context) {
            raw_base *= evaluation_context.reverse_multiplicator;
        }

        return raw_base * evaluation_context.multiplicator;
    },

    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    eval_tax_base_amount(tax_values, evaluation_context) {
        const price_include = tax_values.price_include;
        const amount_type = tax_values.amount_type;
        const total_tax_amount = evaluation_context.total_tax_amount;
        const reverse = evaluation_context.reverse;

        let raw_base =
            evaluation_context.quantity * evaluation_context.price_unit +
            evaluation_context.extra_base;
        if (reverse && "reverse_multiplicator" in evaluation_context) {
            raw_base *= evaluation_context.reverse_multiplicator;
        }
        const base = raw_base - total_tax_amount;

        if (price_include) {
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
        const tax_values_list = taxes_computation.tax_values_list;
        const eval_order_indexes = taxes_computation.eval_order_indexes;
        const rounding_method = evaluation_context.rounding_method;
        const prec_rounding = evaluation_context.precision_rounding;
        const reverse = evaluation_context.reverse;
        let eval_tax_values_list = tax_values_list.map((tax_values) =>
            Object.assign({}, tax_values)
        );
        const skipped = new Set();
        for (const [quid, index] of eval_order_indexes) {
            const tax_values = eval_tax_values_list[index];
            if (quid === "tax") {
                let extra_base = 0.0;
                for (const [extra_base_sign, extra_base_index] of tax_values.extra_base_for_tax) {
                    const target_tax_values = eval_tax_values_list[extra_base_index];
                    if (!reverse || !target_tax_values.price_include) {
                        extra_base += extra_base_sign * target_tax_values.tax_amount_factorized;
                    }
                }
                let tax_amount = this.eval_tax_amount(tax_values, {
                    ...evaluation_context,
                    ...tax_values.evaluation_context,
                    extra_base: extra_base,
                    reverse: reverse,
                });
                if (tax_amount === undefined) {
                    skipped.add(tax_values.id);
                    tax_amount = 0.0;
                }
                tax_values.tax_amount = tax_amount;
                tax_values.tax_amount_factorized = tax_values.tax_amount * tax_values._factor;
                if (rounding_method === "round_per_line") {
                    tax_values.tax_amount_factorized = roundPrecision(
                        tax_values.tax_amount_factorized,
                        prec_rounding
                    );
                }
            } else if (quid === "base") {
                let extra_base = 0.0;
                for (const [extra_base_sign, extra_base_index] of tax_values.extra_base_for_base) {
                    const target_tax_values = eval_tax_values_list[extra_base_index];
                    if (!reverse || !target_tax_values.price_include) {
                        extra_base += extra_base_sign * target_tax_values.tax_amount_factorized;
                    }
                }
                let total_tax_amount = 0.0;
                for (const batch_index of tax_values.batch_indexes) {
                    total_tax_amount += eval_tax_values_list[batch_index].tax_amount_factorized;
                }
                Object.assign(
                    tax_values,
                    this.eval_tax_base_amount(tax_values, {
                        ...evaluation_context,
                        ...tax_values.evaluation_context,
                        extra_base: extra_base,
                        total_tax_amount: total_tax_amount,
                        reverse: reverse,
                    })
                );
                if (rounding_method === "round_per_line") {
                    tax_values.base = roundPrecision(tax_values.base, prec_rounding);
                    tax_values.display_base = roundPrecision(
                        tax_values.display_base,
                        prec_rounding
                    );
                }
            }
        }

        if (skipped.length > 0) {
            eval_tax_values_list = eval_tax_values_list.filter(
                (tax_values) => !skipped.has(tax_values.id)
            );
        }

        let total_excluded = null;
        let total_included = null;
        if (eval_tax_values_list.length > 0) {
            total_excluded = eval_tax_values_list[0].base;
            let tax_amount = 0.0;
            for (const tax_values of eval_tax_values_list) {
                tax_amount += tax_values.tax_amount_factorized;
            }
            total_included = total_excluded + tax_amount;
        } else {
            total_excluded = total_included =
                evaluation_context.quantity * evaluation_context.price_unit;
            if (rounding_method === "round_per_line") {
                total_excluded = total_included = roundPrecision(total_excluded, prec_rounding);
            }
        }

        return {
            tax_values_list: eval_tax_values_list,
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
        original_tax_values_list,
        new_tax_values_list
    ) {
        const original_tax_ids = new Set(original_tax_values_list.map((x) => x.id));
        const new_tax_ids = new Set(new_tax_values_list.map((x) => x.id));
        if (
            (original_tax_ids.size === new_tax_ids.size &&
                [...original_tax_ids].every((value) => new_tax_ids.has(value))) ||
            original_tax_values_list.some((x) => !x.price_include)
        ) {
            return price_unit;
        }

        let taxes_computation = this.prepare_taxes_computation(original_tax_values_list);
        let evaluation_context = this.eval_taxes_computation_prepare_context(
            price_unit,
            1.0,
            product_values,
            { rounding_method: "round_globally" }
        );
        taxes_computation = this.eval_taxes_computation(taxes_computation, evaluation_context);
        price_unit = taxes_computation.total_excluded;

        taxes_computation = this.prepare_taxes_computation(new_tax_values_list);
        evaluation_context = this.eval_taxes_computation_prepare_context(
            price_unit,
            1.0,
            product_values,
            {
                rounding_method: "round_globally",
                reverse: true,
            }
        );
        taxes_computation = this.eval_taxes_computation(taxes_computation, evaluation_context);
        let delta = 0.0;
        for (const tax_values of taxes_computation.tax_values_list) {
            if (tax_values.price_include) {
                delta += tax_values.tax_amount_factorized;
            }
        }
        return price_unit + delta;
    },

    // -------------------------------------------------------------------------
    // PURE JS HELPERS
    // -------------------------------------------------------------------------

    computeSingleLineTaxes(
        tax_values_list,
        evaluation_context,
        { force_price_include = false, is_refund = false, include_caba_tags = false } = {}
    ) {
        const taxes_computation = this.prepare_taxes_computation(tax_values_list, {
            force_price_include: force_price_include,
            is_refund: is_refund,
            include_caba_tags: include_caba_tags,
        });
        return this.eval_taxes_computation(taxes_computation, evaluation_context);
    },
};
