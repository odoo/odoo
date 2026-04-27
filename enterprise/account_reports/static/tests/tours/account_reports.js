/** @odoo-module **/

import { Asserts } from "./asserts";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("account_reports", {
    url: "/odoo/action-account_reports.action_account_report_bs",
    steps: () => [
        //--------------------------------------------------------------------------------------------------------------
        // Foldable
        //--------------------------------------------------------------------------------------------------------------
        {
            content: "Initial foldable",
            trigger: ".o_content",
            run: () => {
                Asserts.DOMContainsNumber("tbody > tr:not(.d-none):not(.empty)", 28);

                // Since the total line is not displayed (folded), the amount should be on the line
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(4) td:nth-child(2)").textContent,
                    "75.00"
                );
            },
        },
        {
            content: "Click to unfold line",
            trigger: "tr:nth-child(4) td:first()",
            run: "click",
        },
        {
            content: "Line is unfolded",
            trigger: "tr:nth-child(5) .name:contains('101401')",
            run: () => {
                Asserts.DOMContainsNumber("tbody > tr:not(.d-none):not(.empty)", 30);

                // Since the total line is displayed (unfolded), the amount should not be on the line
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(4) td:nth-child(2)").textContent,
                    ""
                );
            },
        },
        {
            content: "Click to fold line",
            trigger: "tr:nth-child(4) td:first()",
            run: "click",
        },
        {
            content: "Line is folded",
            trigger: ".o_content",
            run: () => {
                Asserts.DOMContainsNumber("tbody > tr:not(.d-none):not(.empty)", 28);
            },
        },
        //--------------------------------------------------------------------------------------------------------------
        // Sortable
        //--------------------------------------------------------------------------------------------------------------
        {
            content: "Unfold first line",
            trigger: "tr:nth-child(4) td:first()",
            run: "click",
        },
        {
            content: "Unfold second line",
            trigger: "tr:nth-child(7) td:first()",
            run: "click",
        },
        {
            content: "Unfold third line",
            trigger: "tr:nth-child(10) td:first()",
            run: "click",
        },
        {
            content: "Extra Trigger step",
            trigger: "tr:nth-child(12):not(.d-none) .name:contains('101404')",
        },
        {
            content: "Initial sortable",
            trigger: ".o_content",
            run: () => {
                // Bank and Cash Accounts
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(5) td:nth-child(2)").textContent,
                    "75.00"
                );
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(6) td:nth-child(2)").textContent,
                    "75.00"
                );

                // Receivables
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(8) td:nth-child(2)").textContent,
                    "25.00"
                );
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(9) td:nth-child(2)").textContent,
                    "25.00"
                );

                // Current Assets
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(11) td:nth-child(2)").textContent,
                    "100.00"
                );
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(12) td:nth-child(2)").textContent,
                    "50.00"
                );
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(13) td:nth-child(2)").textContent,
                    "150.00"
                );
            },
        },
        {
            content: "Click sort",
            trigger: "th .btn_sortable",
            run: "click",
        },
        {
            trigger: "tr:nth-child(11) td:nth-child(2):contains('50.00')",
        },
        {
            content: "Unfold not previously unfolded line",
            trigger: "tr:nth-child(22):contains('Current Liabilities') td:first()",
            run: "click",
        },
        {
            content: "Line is unfolded",
            trigger: "tr:nth-child(23) .name:contains('251000')",
            run: "click",
        },
        {
            content: "Sortable (asc)",
            trigger: "tr:nth-child(11) td:nth-child(2):contains('50.00')",
            run: () => {
                // Bank and Cash Accounts
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(5) td:nth-child(2)").textContent,
                    "75.00"
                );
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(6) td:nth-child(2)").textContent,
                    "75.00"
                );

                // Receivables
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(8) td:nth-child(2)").textContent,
                    "25.00"
                );
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(9) td:nth-child(2)").textContent,
                    "25.00"
                );

                // Current Assets
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(11) td:nth-child(2)").textContent,
                    "50.00"
                );
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(12) td:nth-child(2)").textContent,
                    "100.00"
                );
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(13) td:nth-child(2)").textContent,
                    "150.00"
                );
            },
        },
        {
            content: "Click sort",
            trigger: "th .btn_sortable",
            run: "click",
        },
        {
            content: "Sortable (desc)",
            trigger: "tr:nth-child(11) td:nth-child(2):contains('100.00')",
            run: () => {
                // Bank and Cash Accounts
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(5) td:nth-child(2)").textContent,
                    "75.00"
                );
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(6) td:nth-child(2)").textContent,
                    "75.00"
                );

                // Receivables
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(8) td:nth-child(2)").textContent,
                    "25.00"
                );
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(9) td:nth-child(2)").textContent,
                    "25.00"
                );

                // Current Assets
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(11) td:nth-child(2)").textContent,
                    "100.00"
                );
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(12) td:nth-child(2)").textContent,
                    "50.00"
                );
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(13) td:nth-child(2)").textContent,
                    "150.00"
                );
            },
        },
        {
            content: "Click sort",
            trigger: "th .btn_sortable",
            run: "click",
        },
        {
            content: "Sortable (reset)",
            trigger: "tr:nth-child(5) td:nth-child(2):contains('75.00')",
            run: () => {
                // Bank and Cash Accounts
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(5) td:nth-child(2)").textContent,
                    "75.00"
                );
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(6) td:nth-child(2)").textContent,
                    "75.00"
                );

                // Receivables
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(8) td:nth-child(2)").textContent,
                    "25.00"
                );
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(9) td:nth-child(2)").textContent,
                    "25.00"
                );

                // Current Assets
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(11) td:nth-child(2)").textContent,
                    "100.00"
                );
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(12) td:nth-child(2)").textContent,
                    "50.00"
                );
                Asserts.isEqual(
                    document.querySelector("tr:nth-child(13) td:nth-child(2)").textContent,
                    "150.00"
                );
            },
        },
    ],
});
