import { assert } from "@stock/../tests/tours/tour_helper";

/**
 * Clicks on the "Catalog" button below the purchase order lines
 */
export function goToCatalogFromPO() {
    return [
        {
            content: "Go to product catalog",
            trigger: 'button[name="action_add_from_catalog"]',
            run: "click",
        },
        { trigger: ".o_kanban_view.o_purchase_product_kanban_catalog_view" },
    ];
}

/**
 * Clicks on the "Back to Order" button from the Catalog view
 */
export function goToPOFromCatalog() {
    return [
        {
            content: "Go back to the PO",
            trigger: "button.o-kanban-button-back",
            run: "click",
        },
        { trigger: ".o_form_view.o_purchase_order" },
    ];
}

/**
 * Sets the Suggest UI parameters
 * @param {string} basedOn The label value of the "Replenish based on" select options (eg. "Last 3 months")
 * @param {number} nbDays The value of the "Replenish for" input (eg. 90)
 * @param {number} factor The value of the "x ...%" input (eg. 50)
 */
export function setSuggestParameters({ basedOn = false, nbDays = false, factor = false }) {
    const steps = [];
    if (basedOn) {
        steps.push(
            {
                trigger: ".o_TimePeriodSelectionField .o_select_menu .dropdown-toggle:visible",
                run: "click",
            },
            {
                trigger: ".o_select_menu_menu:visible",
            },
            {
                trigger: `.o_select_menu_menu .o_select_menu_item:contains('${basedOn}'):visible`,
                run: "click",
            }
        );
    }
    if (nbDays !== false) {
        steps.push({
            trigger: "input.o_PurchaseSuggestInput:eq(0)",
            run: `edit ${nbDays}`,
        });
    }
    if (factor !== false) {
        steps.push({
            trigger: "input.o_PurchaseSuggestInput:eq(1)",
            run: `edit ${factor}`,
        });
    }
    return steps;
}

/**
 * @param {boolean} turnOn True to turn Suggest ON, false to turn it OFF
 */
export function toggleSuggest(turnOn) {
    return [
        {
            trigger: 'div[name="search-suggest-toggle"] input',
            run: "click",
        },
        {
            trigger: `div[name="search-suggest-toggle"] input:${
                turnOn ? "checked" : "not(:checked)"
            }`,
        },
    ];
}

/**
 * Checks a product's Kanban  is highlighted and in a specified place (if passed in param)
 * @param {string} product product display name
 * @param {number | false } expectedOrder 0 is the first card
 * @param {boolean} highlightOn default to true
 */
export function checkKanbanRecordHighlight(product, expectedOrder, highlightOn = true) {
    return {
        trigger: ".o_kanban_view.o_purchase_product_kanban_catalog_view .o_kanban_record",
        run() {
            const cards = [...document.querySelectorAll(".o_kanban_record")];
            if (expectedOrder) {
                assert(expectedOrder + 1 <= cards.length, true, "expectedOrder out of range.");
                assert(cards[expectedOrder].textContent.includes(product), true, "Wrong order");
            }

            const card = cards.find((card) => card.textContent.includes(product));
            if (highlightOn === true) {
                assert(card.className.includes("o_suggest_highlight"), true, "Highlight missing");
            } else if (highlightOn === false) {
                assert(card.className.includes("o_suggest_highlight"), false, "Wrong Highlight");
            }
        },
    };
}
