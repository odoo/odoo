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
            const kwargs = {
                product: params.product,
                precision_rounding: params.precision_rounding,
                rounding_method: params.rounding_method,
            };
            const results = {
                results: accountTaxHelpers.get_tax_details(
                    params.taxes,
                    params.price_unit,
                    params.quantity,
                    kwargs,
                )
            };
            if (params.rounding_method === "round_globally") {
                results.total_excluded_results = accountTaxHelpers.get_tax_details(
                    params.taxes,
                    results.results.total_excluded / params.quantity,
                    params.quantity,
                    {...kwargs, special_mode: "total_excluded"}
                );
                results.total_included_results = accountTaxHelpers.get_tax_details(
                    params.taxes,
                    results.results.total_included / params.quantity,
                    params.quantity,
                    {...kwargs, special_mode: "total_included"}
                );
            }
            return results;
        }
        if (params.test === "adapt_price_unit_to_another_taxes") {
            return {
                price_unit: accountTaxHelpers.adapt_price_unit_to_another_taxes(
                    params.price_unit,
                    params.product,
                    params.original_taxes,
                    params.new_taxes
                )
            }
        }
        if (params.test === "tax_totals_summary") {
            const document = this.populateDocument(params.document);
            const taxTotals = accountTaxHelpers.get_tax_totals_summary(
                document.lines,
                document.currency,
                document.company,
                {cash_rounding: document.cash_rounding}
            );
            return {tax_totals: taxTotals};
        }
        if (params.test === "tax_total") {
            const document = this.populateDocument(params.document);
            const taxTotals = accountTaxHelpers.get_tax_totals_summary(
                document.lines,
                document.currency,
                document.company,
                {cash_rounding: document.cash_rounding}
            );
            return {tax_amount_currency: taxTotals.tax_amount_currency};
        }
    }

    async processTests() {
        const tests = this.props.tests || [];
        const results = tests.map(this.processTest.bind(this));
        await rpc("/account/post_tests_shared_js_python", { results: results });
        this.state.done = true;
    }

    populateDocument(document) {
        const base_lines = document.lines.map(line => accountTaxHelpers.prepare_base_line_for_taxes_computation(null, line));
        accountTaxHelpers.add_tax_details_in_base_lines(base_lines, document.company);
        accountTaxHelpers.round_base_lines_tax_details(base_lines, document.company);
        return {
            ...document,
            lines: base_lines,
        }
    }
}

registry.category("public_components").add("account.tests_shared_js_python", TestsSharedJsPython);
