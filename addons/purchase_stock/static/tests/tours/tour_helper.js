import { assert } from "@stock/../tests/tours/tour_helper";

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
 * Checks a product Kanban is highlighted and in a specified place
 * @param {string} product product display name
 * @param {number} expected_order  1 == [0], 2 == [1] ...
 * @param {boolean} highlightOn default to true
 */
export function checkKanbanRecordHighlight(product, expected_order, highlightOn = true) {
    return {
        trigger: ".o_kanban_view.o_purchase_product_kanban_catalog_view .o_kanban_record",
        run() {
            const cards = [...document.querySelectorAll(".o_kanban_record")];
            const product_card = cards.find((card) => card.textContent.includes(product));
            const highlighted = product_card.className.includes("o_suggest_highlight");
            if (highlightOn === true) {
                assert(highlighted, true, `${product} record should be highlighted.`);
                assert(
                    product_card == cards[expected_order - 1],
                    true,
                    `Card in position ${cards.indexOf(product_card)} not ${expected_order}.`
                );
            } else if (highlightOn === false) {
                assert(highlighted, false, `${product} record should not be highlighted.`);
            }
        },
    };
}
