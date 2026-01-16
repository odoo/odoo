import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

import { accountTaxHelpers } from "@account/helpers/account_tax";

import { useState, Component } from "@odoo/owl";

export class TestsSharedJsPython extends Component {
    static template = "account.TestsSharedJsPython";
    static props = {
        tests: { type: Array, optional: true },
    };

    setup() {
        super.setup();
        this.state = useState({ done: false });
    }

    processTest(params) {
        if (params.test === "taxes_computation") {
            let filter_tax_function = null;
            if (params.excluded_tax_ids && params.excluded_tax_ids.length) {
                filter_tax_function = (tax) => !params.excluded_tax_ids.includes(tax.id);
            }

            const kwargs = {
                product: params.product,
                product_uom: params.product_uom,
                precision_rounding: params.precision_rounding,
                rounding_method: params.rounding_method,
                filter_tax_function: filter_tax_function,
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
                    params.new_taxes,
                    { product_uom: params.product_uom}
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
            return {tax_totals: taxTotals, soft_checking: params.soft_checking};
        }
        if (params.test === "global_discount") {
            const document = this.populateDocument(params.document);
            const baseLines = accountTaxHelpers.prepare_global_discount_lines(
                document.lines,
                document.company,
                params.amount_type,
                params.amount,
                "global_discount",
            );
            document.lines.push(...baseLines);
            accountTaxHelpers.add_tax_details_in_base_lines(document.lines, document.company);
            accountTaxHelpers.round_base_lines_tax_details(document.lines, document.company);
            const taxTotals = accountTaxHelpers.get_tax_totals_summary(
                document.lines,
                document.currency,
                document.company,
                {cash_rounding: document.cash_rounding}
            );
            return {tax_totals: taxTotals, soft_checking: params.soft_checking};
        }
        if (params.test === "down_payment") {
            const document = this.populateDocument(params.document);
            const baseLines = accountTaxHelpers.prepare_down_payment_lines(
                document.lines,
                document.company,
                params.amount_type,
                params.amount,
                "down_payment",
            );
            document.lines = baseLines;
            accountTaxHelpers.add_tax_details_in_base_lines(document.lines, document.company);
            accountTaxHelpers.round_base_lines_tax_details(document.lines, document.company);
            const taxTotals = accountTaxHelpers.get_tax_totals_summary(
                document.lines,
                document.currency,
                document.company,
                {cash_rounding: document.cash_rounding}
            );
            return {
                tax_totals: taxTotals,
                soft_checking: params.soft_checking,
                base_lines_tax_details: this.extractBaseLinesDetails(document),
            };
        }
        if (params.test === "base_lines_tax_details") {
            const document = this.populateDocument(params.document);
            return {
                base_lines_tax_details: this.extractBaseLinesDetails(document),
            };
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

    extractBaseLinesDetails(document) {
        return document.lines.map(line => ({
            total_excluded_currency: line.tax_details.total_excluded_currency,
            total_excluded: line.tax_details.total_excluded,
            total_included_currency: line.tax_details.total_included_currency,
            total_included: line.tax_details.total_included,
            delta_total_excluded_currency: line.tax_details.delta_total_excluded_currency,
            delta_total_excluded: line.tax_details.delta_total_excluded,
            manual_total_excluded_currency: line.manual_total_excluded_currency,
            manual_total_excluded: line.manual_total_excluded,
            manual_tax_amounts: line.manual_tax_amounts,
            taxes_data: line.tax_details.taxes_data.map(tax_data => ({
                tax_id: tax_data.tax.id,
                tax_amount_currency: tax_data.tax_amount_currency,
                tax_amount: tax_data.tax_amount,
                base_amount_currency: tax_data.base_amount_currency,
                base_amount: tax_data.base_amount,
            })),
        }));
    }
}

registry.category("public_components").add("account.tests_shared_js_python", TestsSharedJsPython);
