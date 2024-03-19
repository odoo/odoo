/** @odoo-module **/
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

import { accountTaxHelpers } from "@account/helpers/account_tax";

import { xml, useState, Component } from "@odoo/owl";

export class TestsSharedJsPython extends Component {
    static template = xml`
        <button t-attf-class="#{state.done ? 'text-success' : ''}" t-on-click="processTests">Test</button>
    `;
    static props = {
        tests: { type: Array, optional: true },
    };

    setup() {
        super.setup();
        this.state = useState({ done: false });
    }

    create_document(create_document_params, other_params) {
        let document_values = accountTaxHelpers.create_document_for_taxes_computation(
            ...create_document_params[0],
            create_document_params[1]
        );
        for (let [quid, args, kwargs] of other_params) {
            if (quid === "add_line") {
                document_values.lines.push(accountTaxHelpers.prepare_document_line(...args, kwargs));
            } else if (quid === "add_cash_rounding") {
                accountTaxHelpers.add_cash_rounding_to_document(document_values, ...args, kwargs);
            }
        }
        return document_values;
    }

    get_test_js_tax_totals_summary_results(document_values, { exclude_tax_group_ids = null } = {}) {
        accountTaxHelpers.add_line_tax_amounts_to_document(document_values);
        const results = accountTaxHelpers.get_tax_totals_summary(document_values);
        accountTaxHelpers.apply_cash_rounding_to_tax_totals_summary(document_values, results);
        if(exclude_tax_group_ids !== null){
            debugger;
            accountTaxHelpers.exclude_tax_group_from_tax_totals_summary(results, exclude_tax_group_ids);
        }
        return results;
    }

    get_test_js_total_per_tax_summary_results(document_values) {
        accountTaxHelpers.add_line_tax_amounts_to_document(document_values);
        return accountTaxHelpers.get_total_per_tax_summary(document_values);
    }

    processTest(params) {
        if (params.test === "taxes_computation") {
            const jsResults = {};
            let evaluationContext = accountTaxHelpers.eval_taxes_computation_prepare_context(
                params.price_unit,
                params.quantity,
                params.product_values,
                params.evaluation_context_kwargs
            );
            let taxesComputation = accountTaxHelpers.prepare_taxes_computation(
                params.taxes_data,
                params.compute_kwargs
            );
            jsResults.results = accountTaxHelpers.eval_taxes_computation(
                taxesComputation,
                evaluationContext
            );

            if (params.is_round_globally) {
                let taxesComputation = accountTaxHelpers.prepare_taxes_computation(
                    params.taxes_data,
                    { ...params.compute_kwargs, special_mode: "total_excluded" }
                );
                evaluationContext = accountTaxHelpers.eval_taxes_computation_prepare_context(
                    jsResults.results.total_excluded / params.quantity,
                    params.quantity,
                    params.product_values,
                    params.evaluation_context_kwargs
                );
                jsResults.total_excluded_results = accountTaxHelpers.eval_taxes_computation(
                    taxesComputation,
                    evaluationContext
                );
                taxesComputation = accountTaxHelpers.prepare_taxes_computation(
                    params.taxes_data,
                    { ...params.compute_kwargs, special_mode: "total_included" }
                );
                evaluationContext = accountTaxHelpers.eval_taxes_computation_prepare_context(
                    jsResults.results.total_included / params.quantity,
                    params.quantity,
                    params.product_values,
                    params.evaluation_context_kwargs
                );
                jsResults.total_included_results = accountTaxHelpers.eval_taxes_computation(
                    taxesComputation,
                    evaluationContext
                );
            }
            return jsResults;
        }
        if (params.test === "adapt_price_unit_to_another_taxes") {
            return accountTaxHelpers.adapt_price_unit_to_another_taxes(
                params.price_unit,
                params.product_values,
                params.original_taxes_data,
                params.new_taxes_data
            );
        }
        if (params.test === "tax_totals_summary") {
            const document_values = this.create_document(params.create_document_params, params.other_params);
            return this.get_test_js_tax_totals_summary_results(
                document_values,
                { exclude_tax_group_ids: params.exclude_tax_group_ids }
            );
        }
        if (params.test === "tax_amount") {
            const document_values = this.create_document(params.create_document_params, params.other_params);
            const result = this.get_test_js_tax_totals_summary_results(
                document_values,
                { exclude_tax_group_ids: params.exclude_tax_group_ids }
            );
            return result.tax_amount;
        }
        if (params.test === "total_per_tax_summary") {
            const document_values = this.create_document(params.create_document_params, params.other_params);
            return this.get_test_js_total_per_tax_summary_results(document_values, params.exclude_tax_group_ids);
        }
    }

    async processTests() {
        const tests = this.props.tests || [];
        const results = tests.map(this.processTest.bind(this));
        await rpc("/account/post_tests_shared_js_python", { results: results });
        this.state.done = true;
    }
}

registry.category("public_components").add("account.tests_shared_js_python", TestsSharedJsPython);
