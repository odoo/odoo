import { assert } from "@stock/../tests/tours/tour_helper";

export const catalogSuggestion = {
    /**
     * Sets the Suggest UI parameters.
     * @param {string} basedOn The label value of the "Replenish based on" select options (eg. "Last 3 months")
     * @param {number} nbDays The value of the "Replenish for" input (eg. 90)
     * @param {number} factor The value of the "x ...%" input (eg. 50)
     */
    setParameters({ basedOn = false, nbDays = false, factor = false }) {
        const steps = [];
        if (nbDays) {
            steps.push({
                trigger: "input.o_PurchaseSuggestInput:eq(0)",
                run: `edit ${nbDays}`,
            });
        }
        if (factor) {
            steps.push({
                trigger: "input.o_PurchaseSuggestInput:eq(1)",
                run: `edit ${factor}`,
            });
        }
        // Little trick to add the the basedOn step last because it doesn't have a debounce
        // meaning it will trigger a kanbanReload with the params above already set.
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
        return steps;
    },

    /**
     * Asserts the Suggest UI parameters are saved as expected.
     * @param {string} basedOn The label value of the "Replenish based on" select options (eg. "Last 3 months")
     * @param {number} nbDays The value of the "Replenish for" input (eg. 90)
     * @param {number} factor The value of the "x ...%" input (eg. 50)
     */
    assertParameters({ basedOn = false, nbDays = false, factor = false }) {
        const steps = [];

        if (nbDays) {
            steps.push({
                content: "Check number days saved",
                trigger: "input.o_PurchaseSuggestInput:eq(0)",
                run() {
                    const days = parseInt(this.anchor.value, 10);
                    assert(days, nbDays, `Expected days ${nbDays}, got ${days}`);
                },
            });
        }
        if (factor) {
            steps.push({
                content: "Check percent factor saved",
                trigger: "input.o_PurchaseSuggestInput:eq(1)",
                run() {
                    const percent = parseInt(this.anchor.value, 10);
                    assert(percent, factor, `Expected percent factor ${factor}, got ${percent}`);
                },
            });
        }
        if (basedOn) {
            steps.push({
                content: "Check based-on saved",
                trigger: ".o_TimePeriodSelectionField",
                run() {
                    const drop = this.anchor.querySelector(".o_select_menu_toggler");
                    assert(drop.value, basedOn, `Expected based on ${basedOn}, got ${drop.value}`);
                },
            });
        }

        return steps;
    },

    /**
     * Checks catalog kanban record fields match expectations
     * @param {string} productName The product display name of the card to check
     * @param {number} monthly The product monthly demand
     * @param {number} suggest The product suggested quantity
     * @param {number} forecast The product forecasted quantity
     */
    assertCatalogRecord(productName, { monthly, suggest, forecast } = {}) {
        const steps = [];

        if (monthly) {
            steps.push({
                content: "Check catalog record monthly demand",
                trigger: `.o_kanban_record:contains('${productName}') span[name='kanban_monthly_demand_qty']:visible:contains('${monthly}')`,
            });
        }
        if (suggest) {
            steps.push({
                content: "Check catalog record suggested quantity",
                trigger: `.o_kanban_record:contains('${productName}') div[name='kanban_purchase_suggest'] span:visible:contains('${suggest}')`,
            });
        }
        if (forecast) {
            steps.push({
                content: "Check catalog record forecasted quantity",
                trigger: `.o_kanban_record:contains('${productName}') span[name='o_kanban_forecasted_qty']:visible:contains('${forecast}')`,
            });
        }

        return steps;
    },

    /**
     * @param {boolean} turnOn True to turn Suggest ON, false to turn it OFF
     */
    toggleSuggest(turnOn) {
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
    },

    /**
     * Checks a product Kanban is highlighted and in a specified place
     * @param {string} product product display name
     * @param {number} expected_order  1 == [0], 2 == [1] ...
     * @param {boolean} highlightOn default to true
     */
    checkKanbanRecordHighlight(product, expected_order, highlightOn = true) {
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
    },

    addAllSuggestions() {
        const content = "Add all suggestion to the PO";
        const trigger = 'button[name="suggest_add_all"]';
        return [{ content, trigger, run: "click" }];
    },
};
