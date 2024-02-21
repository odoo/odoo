/** @odoo-module **/
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

import {
    adapt_price_unit_to_another_taxes,
    eval_taxes_computation,
    eval_taxes_computation_prepare_context,
    prepare_taxes_computation,
} from "@account/helpers/account_tax";

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

    processTest(params){
        if(params.test === "taxes_computation"){
            const jsResults = {};
            let evaluationContext = eval_taxes_computation_prepare_context(
                params.price_unit,
                params.quantity,
                params.evaluation_context_kwargs,
            );
            let taxesComputation = prepare_taxes_computation(params.tax_values_list, params.compute_kwargs);
            jsResults.results = eval_taxes_computation(taxesComputation, evaluationContext);

            if(params.is_round_globally){
                evaluationContext = eval_taxes_computation_prepare_context(
                    jsResults.results.total_excluded / params.quantity,
                    params.quantity,
                    {...params.evaluation_context_kwargs, reverse: true},
                );
                jsResults.reverse_results = eval_taxes_computation(taxesComputation, evaluationContext);
            }
            return jsResults;
        }
        if(params.test === "adapt_price_unit_to_another_taxes"){
            return adapt_price_unit_to_another_taxes(
                params.price_unit,
                params.original_tax_values_list,
                params.new_tax_values_list,
            )
        }
    }

    async processTests(){
        const tests = this.props.tests || [];
        const results = tests.map(this.processTest);
        await rpc("/account/post_tests_shared_js_python", {'results': results});
        this.state.done = true;
    }
}

registry.category("public_components").add("account.tests_shared_js_python", TestsSharedJsPython);
