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

function fetchOrderRewardLines(orderUuid) {
    return posmodel.data.call("pos.order.line", "search_read", [
        [
            ["is_reward_line", "=", true],
            ["order_id.uuid", "=", orderUuid],
        ],
        ["uuid"],
    ]);
}

function currentRewardLines() {
    return posmodel.get_order().lines.filter((line) => line.is_reward_line);
}

registry.category("web_tour.tours").add("PosLoyaltyRewardLinesFirstRegisterTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            {
                content: "the discount and the free product are applied",
                trigger: ".orderline.fst-italic",
                run: async () => {
                    await new Promise((resolve) => setTimeout(resolve, 1500));
                    const lines = currentRewardLines();
                    if (lines.length !== 2) {
                        const names = lines.map((line) => line.get_full_product_name());
                        throw new Error(`Expected 2 reward lines, found ${names}`);
                    }
                },
            },
            {
                content: "reward lines get a uuid built from the order and from what they grant",
                trigger: "body",
                run: () => {
                    const order = posmodel.get_order();
                    for (const line of currentRewardLines()) {
                        const product = line._reward_product_id || line.product_id;
                        const grant = line.reward_id.is_global_discount
                            ? "global"
                            : `${line.reward_id.id}_${product.id}`;
                        if (!line.uuid.startsWith(`${order.uuid}-reward-${grant}-`)) {
                            throw new Error(`Unexpected reward line uuid ${line.uuid}`);
                        }
                    }
                },
            },
            {
                content: "a second line granting the same reward gets the next free suffix",
                trigger: "body",
                run: () => {
                    const order = posmodel.get_order();
                    const [freeLine] = currentRewardLines().filter(
                        (line) => !line.reward_id.is_global_discount
                    );
                    const values = {
                        reward_id: freeLine.reward_id,
                        _reward_product_id: freeLine._reward_product_id,
                        product_id: freeLine.product_id,
                        tax_ids: freeLine.tax_ids,
                    };
                    const expected = `${freeLine.uuid}-1`;
                    const uuid = order._getRewardLineUuid(values);
                    if (uuid !== expected) {
                        throw new Error(`Expected suffixed uuid ${expected}, got ${uuid}`);
                    }
                },
            },
            ProductScreen.saveOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyRewardLinesSecondRegisterTour", {
    steps: () => {
        let orderUuid;
        let savedLines;
        return [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.selectOrder("-0001"),
            TicketScreen.loadSelectedOrder(),
            {
                content: "remember the reward lines saved by the first register",
                trigger: ".orderline.fst-italic",
                run: async () => {
                    orderUuid = posmodel.get_order().uuid;
                    savedLines = await fetchOrderRewardLines(orderUuid);
                    if (savedLines.length !== 2) {
                        throw new Error(
                            `Expected 2 saved reward lines, found ${savedLines.length}`
                        );
                    }
                },
            },
            {
                content: "the rebuilt reward lines keep the uuids of the saved ones",
                trigger: "body",
                run: () => {
                    const uuids = currentRewardLines().map((line) => line.uuid).sort();
                    const expected = savedLines.map((line) => line.uuid).sort();
                    if (JSON.stringify(uuids) !== JSON.stringify(expected)) {
                        throw new Error(
                            `Expected ${expected.join(", ")}, found ${uuids.join(", ")}`
                        );
                    }
                },
            },
            ProductScreen.saveOrder(),
            {
                content: "saving from the second register updates the records of the first one",
                trigger: "body",
                run: async () => {
                    const lines = await fetchOrderRewardLines(orderUuid);
                    const ids = lines.map((line) => line.id).sort();
                    const expected = savedLines.map((line) => line.id).sort();
                    if (JSON.stringify(ids) !== JSON.stringify(expected)) {
                        throw new Error(`Expected reward lines ${expected}, found ${ids}`);
                    }
                },
            },
        ].flat();
    },
});
