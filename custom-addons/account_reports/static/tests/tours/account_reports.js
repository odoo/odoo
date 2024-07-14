/** @odoo-module **/

import { Asserts } from "./asserts";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('account_reports', {
    url: "/web?#action=account_reports.action_account_report_bs",
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
                Asserts.isEqual(document.querySelector("tr:nth-child(3) td:nth-child(2)").textContent, "75.00");
            }
        },
        {
            content: "Click to unfold line",
            trigger: "tr:nth-child(3) td:first()",
            run: "click",
        },
        {
            content: "Line is unfolded",
            trigger: "tr:nth-child(4) .name:contains('101401')",
            run: () => {
                Asserts.DOMContainsNumber("tbody > tr:not(.d-none):not(.empty)", 30);

                // Since the total line is displayed (unfolded), the amount should not be on the line
                Asserts.isEqual(document.querySelector("tr:nth-child(3) td:nth-child(2)").textContent, "");
            }
        },
        {
            content: "Click to fold line",
            trigger: "tr:nth-child(3) td:first()",
            run: "click",
        },
        {
            content: "Line is folded",
            trigger: ".o_content",
            run: () => {
                Asserts.DOMContainsNumber("tbody > tr:not(.d-none):not(.empty)", 28);
            }
        },
        //--------------------------------------------------------------------------------------------------------------
        // Footnotes
        //--------------------------------------------------------------------------------------------------------------
        // Test the initial status of footnotes - There is 2 footnotes to display
        {
            content: "Initial footnotes",
            trigger: ".o_content",
            run: () => {
                Asserts.DOMContainsNone(".footnotes");
            }
        },
        {
            content: "Unfold first line",
            trigger: "tr:nth-child(3) td:first()",
            run: "click",
        },
        {
            content: "Unfold second line",
            trigger: "tr:nth-child(6) td:first()",
            run: "click",
        },
        {
            content: "Unfold third line",
            trigger: "tr:nth-child(9) td:first()",
            run: "click",
        },
        {
            content: "Check order on lines and footnotes",
            trigger: ".o_content",
            extra_trigger: "tr:nth-child(11):not(.d-none) .name:contains('101404')",
            run: () => {
                // Check line number
                Asserts.isEqual(document.querySelector("tr:nth-child(4) sup a").textContent, "1");
                Asserts.isEqual(document.querySelector("tr:nth-child(11) sup a").textContent, "2");

                // Check line number href
                Asserts.isTrue(document.querySelector("tr:nth-child(4) sup a").href.endsWith("#footnote_1"));
                Asserts.isTrue(document.querySelector("tr:nth-child(11) sup a").href.endsWith("#footnote_2"));

                // Check footnotes
                const footnotes = document.querySelectorAll(".footnotes li");

                Asserts.isTrue(footnotes[0].textContent.includes("Footnote 101401"));
                Asserts.isTrue(footnotes[1].textContent.includes("Footnote 101404"));
            }
        },
        // Test that we can add a new footnote
        {
            content: "Click to show caret option",
            trigger: "tr:nth-child(7) .dropdown-toggle",
            run: "click",
        },
        {
            content: "Caret option is displayed",
            trigger: "tr:nth-child(7)",
            run: () => {
                Asserts.hasClass("tr:nth-child(7) .dropdown", "show");
            }
        },
        {
            content: "Click on annotate",
            trigger: "tr:nth-child(7) .dropdown-menu .dropdown-item:last-of-type:contains('Annotate')",
            run: "click"
        },
        {
            content: "Annotate is displayed",
            trigger: ".o_web_client",
            in_modal: false,
            run: () => {
                Asserts.hasClass(".o_web_client", "modal-open");
            }
        },
        {
            content: "Add text to annotate",
            trigger: "textarea",
            run: "text Footnote 121000"
        },
        {
            content: "Submit footnote",
            trigger: ".btn.btn-primary",
            run: "click"
        },
        {
            content: "Check order on lines and footnotes after new footnote added",
            trigger: ".o_content .footnotes #footnote_3",
            run: () => {
                // Check line number
                Asserts.isEqual(document.querySelector("tr:nth-child(4) sup a").textContent, "1");
                Asserts.isEqual(document.querySelector("tr:nth-child(7) sup a").textContent, "2");
                Asserts.isEqual(document.querySelector("tr:nth-child(11) sup a").textContent, "3");

                // Check line number href
                Asserts.isTrue(document.querySelector("tr:nth-child(4) sup a").href.endsWith("#footnote_1"));
                Asserts.isTrue(document.querySelector("tr:nth-child(7) sup a").href.endsWith("#footnote_2"));
                Asserts.isTrue(document.querySelector("tr:nth-child(11) sup a").href.endsWith("#footnote_3"));

                // Check footnotes
                const footnotes = document.querySelectorAll(".footnotes li");

                Asserts.isTrue(footnotes[0].textContent.includes("Footnote 101401"));
                Asserts.isTrue(footnotes[1].textContent.includes("Footnote 121000"));
                Asserts.isTrue(footnotes[2].textContent.includes("Footnote 101404"));
            }
        },
        // Test that we can edit a footnote
        {
            content: "Click to show caret option",
            trigger: "tr:nth-child(7) .dropdown-toggle",
            run: "click",
        },
        {
            content: "Click on annotate",
            trigger: "tr:nth-child(7) .dropdown-menu .dropdown-item:last-of-type:contains('Annotate')",
            run: "click"
        },
        {
            content: "Annotate contains previous text value",
            trigger: "textarea:contains('Footnote 121000')",
        },
        {
            content: "Add text to annotate",
            trigger: "textarea",
            run: "text Footnote 121000 edited"
        },
        {
            content: "Submit footnote",
            trigger: ".btn.btn-primary",
            run: "click"
        },
        {
            content: "Footnote is edited",
            trigger: "#footnote_2:contains('Footnote 121000 edited')",
        },
        // Test that we can delete a footnote by removing the text when editing
        {
            content: "Click to show caret option",
            trigger: "tr:nth-child(7) .dropdown-toggle",
            run: "click",
        },
        {
            content: "Click on annotate",
            trigger: "tr:nth-child(7) .dropdown-menu .dropdown-item:last-of-type:contains('Annotate')",
            run: "click"
        },
        {
            content: "Remove text from annotate",
            trigger: "textarea",
            run: () => {
                document.querySelector(".modal-body textarea").value = "";
            }
        },
        {
            content: "Submit footnote",
            trigger: ".btn.btn-primary",
            run: "click"
        },
        {
            content: "Check order on lines and footnotes after footnote is deleted",
            trigger: "#footnote_2:contains('Footnote 101404')",
            run: () => {
                // Check line number
                Asserts.isEqual(document.querySelector("tr:nth-child(4) sup a").textContent, "1");
                Asserts.isEqual(document.querySelector("tr:nth-child(11) sup a").textContent, "2");

                // Check line number href
                Asserts.isTrue(document.querySelector("tr:nth-child(4) sup a").href.endsWith("#footnote_1"));
                Asserts.isTrue(document.querySelector("tr:nth-child(11) sup a").href.endsWith("#footnote_2"));

                // Check footnotes
                const footnotes = document.querySelectorAll(".footnotes li");

                Asserts.isTrue(footnotes[0].textContent.includes("Footnote 101401"));
                Asserts.isTrue(footnotes[1].textContent.includes("Footnote 101404"));
            }
        },
        // Test that we can delete a footnote by clicking on the trash can next to it
        {
            content: "Click on trash can",
            trigger: "#footnote_1 .fa-trash-o",
            run: "click"
        },
        {
            content: "Check order on lines and footnotes after footnote is deleted",
            trigger: "#footnote_1:contains('Footnote 101404')",
            run: () => {
                // Check line number
                Asserts.isEqual(document.querySelector("tr:nth-child(11) sup a").textContent, "1");

                // Check line number href
                Asserts.isTrue(document.querySelector("tr:nth-child(11) sup a").href.endsWith("#footnote_1"));

                // Check footnotes
                const footnotes = document.querySelectorAll(".footnotes li");

                Asserts.isTrue(footnotes[0].textContent.includes("Footnote 101404"));
            }
        },
        //--------------------------------------------------------------------------------------------------------------
        // Sortable
        //--------------------------------------------------------------------------------------------------------------
        {
            content: "Initial sortable",
            trigger: ".o_content",
            run: () => {
                // Bank and Cash Accounts
                Asserts.isEqual(document.querySelector("tr:nth-child(4) td:nth-child(2)").textContent, "75.00");
                Asserts.isEqual(document.querySelector("tr:nth-child(5) td:nth-child(2)").textContent, "75.00");

                // Receivables
                Asserts.isEqual(document.querySelector("tr:nth-child(7) td:nth-child(2)").textContent, "25.00");
                Asserts.isEqual(document.querySelector("tr:nth-child(8) td:nth-child(2)").textContent, "25.00");

                // Current Assets
                Asserts.isEqual(document.querySelector("tr:nth-child(10) td:nth-child(2)").textContent, "100.00");
                Asserts.isEqual(document.querySelector("tr:nth-child(11) td:nth-child(2)").textContent, "50.00");
                Asserts.isEqual(document.querySelector("tr:nth-child(12) td:nth-child(2)").textContent, "150.00");
            }
        },
        {
            content: "Click sort",
            trigger: "th .btn_sortable",
            run: "click"
        },
        {
            content: "Unfold not previously unfolded line",
            trigger: "tr:nth-child(34):contains('Current Liabilities') td:first()",
            run: "click",
        },
        {
            content: "Line is unfolded",
            trigger: "tr:nth-child(35) .name:contains('251000')",
        },
        {
            content: "Sortable (asc)",
            trigger: "tr:nth-child(18) td:nth-child(2):contains('25.00')",
            run: () => {
                // Receivables
                Asserts.isEqual(document.querySelector("tr:nth-child(18) td:nth-child(2)").textContent, "25.00");
                Asserts.isEqual(document.querySelector("tr:nth-child(19) td:nth-child(2)").textContent, "25.00");

                // Bank and Cash Accounts
                Asserts.isEqual(document.querySelector("tr:nth-child(21) td:nth-child(2)").textContent, "75.00");
                Asserts.isEqual(document.querySelector("tr:nth-child(22) td:nth-child(2)").textContent, "75.00");

                // Current Assets
                Asserts.isEqual(document.querySelector("tr:nth-child(24) td:nth-child(2)").textContent, "50.00");
                Asserts.isEqual(document.querySelector("tr:nth-child(25) td:nth-child(2)").textContent, "100.00");
                Asserts.isEqual(document.querySelector("tr:nth-child(26) td:nth-child(2)").textContent, "150.00");
            }
        },
        {
            content: "Click sort",
            trigger: "th .btn_sortable",
            run: "click"
        },
        {
            content: "Sortable (desc)",
            trigger: "tr:nth-child(4) td:nth-child(2):contains('100.00')",
            run: () => {
                // Current Assets
                Asserts.isEqual(document.querySelector("tr:nth-child(4) td:nth-child(2)").textContent, "100.00");
                Asserts.isEqual(document.querySelector("tr:nth-child(5) td:nth-child(2)").textContent, "50.00");
                Asserts.isEqual(document.querySelector("tr:nth-child(6) td:nth-child(2)").textContent, "150.00");

                // Bank and Cash Accounts
                Asserts.isEqual(document.querySelector("tr:nth-child(8) td:nth-child(2)").textContent, "75.00");
                Asserts.isEqual(document.querySelector("tr:nth-child(9) td:nth-child(2)").textContent, "75.00");

                // Receivables
                Asserts.isEqual(document.querySelector("tr:nth-child(11) td:nth-child(2)").textContent, "25.00");
                Asserts.isEqual(document.querySelector("tr:nth-child(12) td:nth-child(2)").textContent, "25.00");
            }
        },
        {
            content: "Click sort",
            trigger: "th .btn_sortable",
            run: "click"
        },
        {
            content: "Sortable (reset)",
            trigger: "tr:nth-child(4) td:nth-child(2):contains('75.00')",
            run: () => {
                // Bank and Cash Accounts
                Asserts.isEqual(document.querySelector("tr:nth-child(4) td:nth-child(2)").textContent, "75.00");
                Asserts.isEqual(document.querySelector("tr:nth-child(5) td:nth-child(2)").textContent, "75.00");

                // Receivables
                Asserts.isEqual(document.querySelector("tr:nth-child(7) td:nth-child(2)").textContent, "25.00");
                Asserts.isEqual(document.querySelector("tr:nth-child(8) td:nth-child(2)").textContent, "25.00");

                // Current Assets
                Asserts.isEqual(document.querySelector("tr:nth-child(10) td:nth-child(2)").textContent, "100.00");
                Asserts.isEqual(document.querySelector("tr:nth-child(11) td:nth-child(2)").textContent, "50.00");
                Asserts.isEqual(document.querySelector("tr:nth-child(12) td:nth-child(2)").textContent, "150.00");
            }
        },
    ],
});
