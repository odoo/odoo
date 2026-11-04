/* global posmodel */
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import { registry } from "@web/core/registry";

function fetchSavedRewardLines() {
    return posmodel.data.call("pos.order.line", "search_read", [
        [
            ["is_reward_line", "=", true],
            ["order_id.session_id", "=", posmodel.session.id],
        ],
        ["uuid"],
    ]);
}

registry.category("web_tour.tours").add("PosLoyaltyRewardLineIdentityTour", {
    steps: () => {
        let savedLine;
        return [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Organizer", "3"),
            { content: "the automatic discount is applied", trigger: ".orderline.fst-italic" },
            ProductScreen.saveOrder(),
            {
                content: "remember the saved reward line",
                trigger: "body",
                run: async () => {
                    [savedLine] = await fetchSavedRewardLines();
                },
            },
            Chrome.clickMenuOption("Orders"),
            TicketScreen.selectOrder("-0001"),
            TicketScreen.loadSelectedOrder(),
            { content: "the reopened order shows the discount", trigger: ".orderline.fst-italic" },
            {
                content: "the rebuilt reward line keeps the uuid of the saved one",
                trigger: "body",
                run: () => {
                    const uuids = posmodel
                        .get_order()
                        .lines.filter((line) => line.is_reward_line)
                        .map((line) => line.uuid);
                    if (uuids.length !== 1 || uuids[0] !== savedLine.uuid) {
                        throw new Error(
                            `Expected reward line ${savedLine.uuid}, found ${uuids.join(", ")}`
                        );
                    }
                },
            },
            ProductScreen.saveOrder(),
            {
                content: "saving the rebuilt line updates the record already saved",
                trigger: "body",
                run: async () => {
                    const lines = await fetchSavedRewardLines();
                    if (lines.length !== 1 || lines[0].id !== savedLine.id) {
                        throw new Error(
                            `Expected only reward line ${savedLine.id}, found ${lines
                                .map((line) => line.id)
                                .join(", ")}`
                        );
                    }
                },
            },
        ].flat();
    },
});
