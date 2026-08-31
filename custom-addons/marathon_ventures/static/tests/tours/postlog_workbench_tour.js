/**
 * Tour for the Postlog Workbench client action.
 *
 * Proves the OWL component mounts, the filters drive a real RPC, and a matched
 * row reaches the DOM. Driven from tests/test_postlog_workbench_ui.py, which
 * creates the "UI Test Network" fixtures this tour expects.
 */
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("postlog_workbench_tour", {
    steps: () => [
        {
            content: "the workbench mounted",
            trigger: ".mv-fuzzy__page-title:contains('Postlog Workbench')",
        },
        {
            content: "the dropped Version filter is not rendered",
            trigger: ".mv-fuzzy__filter-grid",
            run() {
                const text = document.querySelector(".mv-fuzzy__filter-grid").textContent;
                if (text.includes("Version")) {
                    throw new Error("the Version filter is still rendered");
                }
            },
        },
        {
            content: "the dropped Removed tab is not rendered",
            trigger: ".mv-fuzzy",
            run() {
                const tabs = document.querySelector(".mv-fuzzy__tabs");
                if (tabs && /Removed/.test(tabs.textContent)) {
                    throw new Error("the Removed tab is still rendered");
                }
            },
        },
        {
            content: "pick the program",
            trigger: ".mv-fuzzy__filter-grid select",
            // The generic "select" helper matches an option by its VALUE, and
            // these options are keyed by program id with the name as the label.
            // Find the option by its text and set the value explicitly.
            run() {
                const select = document.querySelector(".mv-fuzzy__filter-grid select");
                const option = [...select.options].find(
                    (o) => o.textContent.trim() === "UI Test Network");
                if (!option) {
                    throw new Error("UI Test Network is not in the Program dropdown");
                }
                select.value = option.value;
                select.dispatchEvent(new Event("change", { bubbles: true }));
            },
        },
        {
            content: "set the broadcast week",
            trigger: ".mv-fuzzy__filter-grid input[type=date]",
            // The generic "edit" helper types into the field character by
            // character, which a native date input rejects. Set the value and
            // fire the change the component listens for.
            run() {
                const input = document.querySelector(
                    ".mv-fuzzy__filter-grid input[type=date]");
                input.value = "2026-07-27";
                input.dispatchEvent(new Event("change", { bubbles: true }));
            },
        },
        {
            content: "run the query",
            trigger: ".mv-fuzzy__filter-actions .btn-primary",
            run: "click",
        },
        {
            content: "the fixture row rendered",
            trigger: "td:contains('UI Fixture Product')",
        },
        {
            content: "the deal number rendered",
            trigger: ".mv-fuzzy:contains('UIT-1')",
        },
        {
            content: "the suggested schedule rendered",
            trigger: ".mv-fuzzy:contains('A-')",
        },
    ],
});
