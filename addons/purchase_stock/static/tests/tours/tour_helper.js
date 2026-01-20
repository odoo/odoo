import { assert } from "@stock/../tests/tours/tour_helper";

export const catalogSuggestion = {
    /**
     * Sets the Suggest UI parameters.
     * @param {string} [basedOn] The label value of the "Replenish based on" select options (eg. "Last 3 months")
     * @param {number} [nbDays] The value of the "Replenish for" input (eg. 90)
     * @param {number} [factor] The value of the "x ...%" input (eg. 50)
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
     * @param {string} [basedOn] The label value of the "Replenish based on" select options (eg. "Last 3 months")
     * @param {number} [nbDays] The value of the "Replenish for" input (eg. 90)
     * @param {number} [factor] The value of the "x ...%" input (eg. 50)
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
     * @param {number | string} [monthly] The product monthly demand
     * @param {number} [suggest] The product suggested quantity
     * @param {number} [forecast] The product forecasted quantity
     */
    assertCatalogRecord(productName, { monthly, suggest, forecast } = {}) {
        const steps = [];
        const card = `.o_kanban_record:contains('${productName}')`;
        monthly &&
            steps.push({
                content: "Check catalog record monthly demand for product ${productName}",
                trigger: `${card} div[name='monthly_demand'] span:visible:text('${monthly}')`,
            });
        suggest &&
            steps.push({
                content: `Check catalog record suggested quantity for product ${productName}`,
                trigger: `${card} div[name='kanban_purchase_suggest'] span:visible:text('${suggest}')`,
            });
        forecast &&
            steps.push({
                content: `Check catalog record forecasted quantity for product ${productName}`,
                trigger: `${card} span[name='o_kanban_forecasted_qty']:visible:text('${forecast}')`,
            });
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
     * Checks a product's record order in Kanban
     * @param {string} product product display name
     * @param {number } expectedOrder 0 is the first card
     */
    checkKanbanRecordPosition(product, expectedOrder) {
        const trigger = `.o_purchase_product_kanban_catalog_view article.o_kanban_record:nth-child(${
            expectedOrder + 1
        }):contains("${product}")`;
        return [{ trigger }];
    },

    removeSuggestFilter() {
        const content = "Remove the Suggested filter";
        const trigger = '.o_facet_value:contains("Suggested")';
        const run = async (actions) => {
            const filters = [...document.querySelectorAll(".o_searchview_facet")];
            const suggestedFilter = filters.find((el) => el.textContent.includes("Suggested"));
            await actions.click(suggestedFilter.querySelector(".o_facet_remove"));
        };
        return [{ content, trigger, run }];
    },

    addAllSuggestions() {
        const content = "Add all suggestion to the PO";
        const trigger = 'button[name="suggest_add_all"]';
        return [{ content, trigger, run: "click" }];
    },
};
