/** @odoo-module */
import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";

export function search(searchWord) {
    return [
        {
            trigger: ".order-management-screen .search-box input",
            run: `text ${searchWord}`,
        },
        {
            trigger: ".order-management-screen .search-box input",
            run: function () {
                const input = document.querySelector(".order-management-screen .search-box input");
                input.dispatchEvent(new KeyboardEvent("keydown", {
                    key: "Enter",
                    code: "Enter",
                    bubbles: true,
                }));
            },
        },
        Chrome.isSynced(),
    ];
}

export function countNumberOfRows(shouldbe) {
    return [{
        trigger: '.order-list .order-row:last-child',
        run: () => {
            const count = document.querySelectorAll('.order-list .order-row').length;
            if (count !== shouldbe) {
                throw new Error(`Expected ${shouldbe} rows, but found ${count}`);
            }
        }
    }];
}
