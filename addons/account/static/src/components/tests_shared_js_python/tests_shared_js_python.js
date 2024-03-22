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

    processTest(params) {
        if (params.test === "taxes_computation") {
            const jsResults = {};
            let evaluationContext = accountTaxHelpers.eval_taxes_computation_prepare_context(
                params.price_unit,
                params.quantity,
                params.product_values,
                params.evaluation_context_kwargs
            );
            const taxesComputation = accountTaxHelpers.prepare_taxes_computation(
                params.taxes_data,
                params.compute_kwargs
            );
            jsResults.results = accountTaxHelpers.eval_taxes_computation(
                taxesComputation,
                evaluationContext
            );

            if (params.is_round_globally) {
                evaluationContext = accountTaxHelpers.eval_taxes_computation_prepare_context(
                    jsResults.results.total_excluded / params.quantity,
                    params.quantity,
                    params.product_values,
                    { ...params.evaluation_context_kwargs, reverse: true }
                );
                jsResults.reverse_results = accountTaxHelpers.eval_taxes_computation(
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
    }

    async processTests() {
        const tests = this.props.tests || [];
        const results = tests.map(this.processTest);
        await rpc("/account/post_tests_shared_js_python", { results: results });
        this.state.done = true;
    }
}

registry.category("public_components").add("account.tests_shared_js_python", TestsSharedJsPython);
