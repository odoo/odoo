import { registry } from "@web/core/registry";

function selectCardStep(cardTitle, ordersCount) {
    return {
        content: `Select the "${cardTitle}" card and register its order count`,
        trigger: `.o_dashboard_card[title='${cardTitle}'] .o_dashboard_card_data`,
        run: async (helpers) => {
            const cardData = document.querySelector(
                `.o_dashboard_card[title='${cardTitle}'] .o_dashboard_card_data`
            );
            ordersCount[cardTitle] = parseInt(cardData.textContent);
            await helpers.click();
        },
    };
}

function checkCardCountStep(cardTitle, ordersCount, countShift) {
    return {
        content: `There should be ${countShift} ${cardTitle} compared to the start`,
        trigger: `.o_dashboard_card`,
        run: async (helpers) => {
            const count = ordersCount[cardTitle] + countShift;
            await helpers.waitUntil(() => {
                if (count === 0) {
                    return document.querySelector(
                        `body:not(:has(.o_dashboard_card[title='${cardTitle}']))`
                    );
                } else {
                    const cardData = document.querySelector(
                        `.o_dashboard_card[title='${cardTitle}'] .o_dashboard_card_data`
                    );
                    return cardData && parseInt(cardData.textContent) === count;
                }
            });
        },
    };
}

registry.category("web_tour.tours").add("test_dashboard_refresh", {
    url: "/odoo/ecommerce-orders",
    steps: () => {
        const ordersCount = {};
        return [
            selectCardStep("Orders to Confirm", ordersCount),
            {
                trigger: ".o_dashboard_card[title='Orders to Confirm'].active",
            },
            {
                trigger: ".o_list_table .o_data_row:contains('Quotation Sent')",
            },
            {
                content: "Select the first order",
                trigger: ".o_list_table .o_data_row .o-checkbox input",
                run: "click",
            },
            {
                trigger: ".o_data_row_selected",
            },
            {
                content: "Confirm it using the header button",
                trigger: ".o_control_panel button[string='Confirm Orders']",
                run: "click",
            },
            checkCardCountStep("Orders to Confirm", ordersCount, -1),
            {
                content: "Select the second order",
                trigger: ".o_list_table .o_data_row .o-checkbox input",
                run: "click",
            },
            {
                trigger: ".o_data_row_selected",
            },
            {
                trigger: ".o_cp_action_menus button.o-dropdown:contains('Action')",
                run: "click",
            },
            {
                content: "Confirm it using the action",
                trigger: ".o-dropdown-item:contains('Confirm Orders')",
                run: "click",
            },
            checkCardCountStep("Orders to Confirm", ordersCount, -2),
            selectCardStep("Orders to Invoice", ordersCount),
            {
                trigger: ".o_dashboard_card[title='Orders to Invoice'].active",
            },
            {
                trigger:
                    ".o_list_table .o_data_row .text-info[name='invoice_status']:contains('To Invoice')",
            },
            {
                content: "Select the first order",
                trigger: ".o_list_table .o_data_row .o-checkbox input",
                run: "click",
            },
            {
                trigger: ".o_data_row_selected",
            },
            {
                trigger: ".o_cp_action_menus button.o-dropdown:contains('Action')",
                run: "click",
            },
            {
                content: "Close it using the action",
                trigger: ".o-dropdown-item:contains('Close Invoicing')",
                run: "click",
            },
            checkCardCountStep("Orders to Invoice", ordersCount, -1),
        ];
    },
});
