import { LunchKanbanRenderer } from "@lunch/views/kanban";
import { defineMailModels, mailModels } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

const lunchInfos = {
    username: "Johnny Hache",
    wallet: 12.05,
    wallet_with_config: 12.05,
    is_manager: false,
    currency: {
        symbol: "€",
        position: "after",
    },
    user_location: [1, "Old Office"],
    alerts: [],
    lines: [],
};

async function mountLunchView() {
    return mountView({
        type: "kanban",
        resModel: "lunch.product",
        arch: `
            <kanban js_class="lunch_kanban">
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                        <field name="price"/>
                    </t>
                </templates>
            </kanban>`,
    });
}

class Product extends models.Model {
    _name = "lunch.product";

    name = fields.Char();
    is_available_at = fields.Integer({ string: "Available" });
    price = fields.Float();

    _records = [
        { id: 1, name: "Big Plate", is_available_at: 1, price: 4.95 },
        { id: 2, name: "Small Plate", is_available_at: 2, price: 6.99 },
        { id: 3, name: "Just One Plate", is_available_at: 2, price: 5.87 },
    ];
}

class Location extends models.Model {
    _name = "lunch.location";

    name = fields.Char();

    _records = [
        { id: 1, name: "Old Office" },
        { id: 2, name: "New Office" },
    ];
}

class Order extends models.Model {
    _name = "lunch.order";

    product_id = fields.Many2one({
        string: "Product",
        relation: "lunch.product",
    });

    _views = {
        form: `<form>
            <sheet>
                <field name="product_id" readonly="1"/>
            </sheet>
            <footer>
                <button name="add_to_cart" type="object" string="Add to cart" />
                <button string="Discard" special="cancel"/>
            </footer>
        </form>`,
    };
}

defineMailModels();
defineModels([Product, Location, Order]);

describe.current.tags("desktop");

onRpc("/lunch/user_location_get", function () {
    return this.env["lunch.location"][0].id;
});
onRpc("/lunch/infos", () => lunchInfos);

test("Basic rendering", async () => {
    await mountLunchView();

    expect(".o_lunch_banner").toHaveCount(1);
    expect(".o_lunch_content .alert").toHaveCount(0);
    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);
    expect(".o_lunch_banner .lunch_user span").toHaveText("Johnny Hache");
});

test("Open product", async () => {
    expect.assertions(2);

    await mountLunchView();

    patchWithCleanup(LunchKanbanRenderer.prototype, {
        openOrderLine(productId, orderId) {
            expect(productId).toBe(1);
        },
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);

    await contains(".o_kanban_record:not(.o_kanban_ghost)").click();
});

test("Basic rendering with alerts", async () => {
    expect.assertions(2);

    const userInfos = {
        ...lunchInfos,
        alerts: [
            {
                id: 1,
                message: "<b>free boudin compote for everyone</b>",
            },
        ],
    };
    onRpc("/lunch/user_location_get", () => userInfos.user_location[0]);
    onRpc("/lunch/infos", () => userInfos);

    await mountLunchView();

    expect(".o_lunch_content .alert").toHaveCount(1);
    expect(".o_lunch_content .alert").toHaveText("free boudin compote for everyone");
});

test("Location change", async () => {
    expect.assertions(3);

    const userInfos = { ...lunchInfos };
    onRpc("/lunch/user_location_get", () => userInfos.user_location[0]);
    onRpc("/lunch/user_location_set", async (request) => {
        const { params } = await request.json();
        expect(params.location_id).toBe(2);
        userInfos.user_location = [2, "New Office"];
        return true;
    });
    await mountLunchView();

    await contains(".lunch_location input").click();

    expect(".lunch_location .dropdown-item:contains(New Office)").toHaveCount(1);

    await contains(
        ".lunch_location li:not(.o_m2o_dropdown_option) .dropdown-item:not(.ui-state-active)"
    ).click();

    expect("article.o_kanban_record").toHaveCount(2);
});

test("Manager: user change", async () => {
    expect.assertions(8);

    mailModels.ResUsers._records.push(
        { id: 1, name: "Johnny Hache" },
        { id: 2, name: "David Elora" }
    );
    let userInfos = { ...lunchInfos, is_manager: true };
    let expectedUserId = false; // false as we are requesting for the current user
    onRpc("/lunch/user_location_get", () => userInfos.user_location[0]);
    onRpc("/lunch/infos", async (request) => {
        const { params } = await request.json();
        expect(expectedUserId).toBe(params.user_id);
        if (expectedUserId === 2) {
            userInfos = {
                ...userInfos,
                username: "David Elora",
                wallet: -10000,
            };
        }
        return userInfos;
    });
    onRpc("/lunch/user_location_set", async (request) => {
        const { params } = await request.json();
        expect(params.location_id).toBe(2);
        userInfos.user_location = [2, "New Office"];
        return true;
    });
    await mountLunchView();

    expect(".lunch_user input").toHaveCount(1);
    await contains(".lunch_user input").click();

    expect(".lunch_user .dropdown-item:contains(David Elora)").toHaveCount(1);

    expectedUserId = 2;
    await contains(".lunch_user li:not(.o_m2o_dropdown_option) .dropdown-item:eq(3)").click();

    expect(".o_lunch_banner .w-100 > .d-flex > span:nth-child(2)").toHaveText("-10000.00\n€", {
        message: "David Elora is poor",
    });

    await contains(".lunch_location input").click();
    await contains(".lunch_location li:not(.o_m2o_dropdown_option) .dropdown-item:eq(1)").click();
    expect(".lunch_user input").toHaveValue("David Elora", {
        message: "changing location should not reset user",
    });
});

test("Trash existing order", async () => {
    expect.assertions(5);

    let userInfos = {
        ...lunchInfos,
        lines: [
            {
                id: 1,
                product: [1, "Big Plate", "4.95", 4.95],
                toppings: [],
                quantity: 1,
                price: 4.95,
                raw_state: "new",
                state: "To Order",
                note: false,
            },
        ],
        raw_state: "new",
        total: "4.95",
        paid_subtotal: "0",
        unpaid_subtotal: "4.95",
    };
    onRpc("/lunch/user_location_get", () => userInfos.user_location[0]);
    onRpc("/lunch/infos", () => userInfos);
    onRpc("/lunch/trash", () => {
        userInfos = {
            ...userInfos,
            lines: [],
            raw_state: false,
            total: 0,
        };
        return true;
    });
    await mountLunchView();

    expect("div.o_lunch_banner > .row > div").toHaveCount(3);
    expect("div.o_lunch_banner > .row > div:nth-child(2) button.fa-trash").toHaveCount(1, {
        message: "should have trash icon",
    });
    expect("div.o_lunch_banner > .row > div:nth-child(2) table > tr").toHaveCount(1, {
        message: "should have one order line",
    });

    expect("div.o_lunch_banner > .row > div:nth-child(3) button:contains(Order Now)").toHaveCount(
        1
    );

    await contains("div.o_lunch_banner > .row > div:nth-child(2) button.fa-trash").click();
    expect("div.o_lunch_banner > .row > div").toHaveCount(1);
});

test("Change existing order", async () => {
    expect.assertions(1);

    let userInfos = {
        ...lunchInfos,
        lines: [
            {
                id: 1,
                product: [1, "Big Plate", "4.95", 4.95],
                toppings: [],
                quantity: 1,
                price: 4.95,
                raw_state: "new",
                state: "To Order",
                note: false,
            },
        ],
        raw_state: "new",
        total: "4.95",
        paid_subtotal: "0",
        unpaid_subtotal: "4.95",
    };
    onRpc("/lunch/user_location_get", () => userInfos.user_location[0]);
    onRpc("/lunch/infos", () => userInfos);
    onRpc("lunch.order", "update_quantity", ({ args }) => {
        expect(args[1]).toBe(1, { message: "should increment order quantity by 1" });
        userInfos = {
            ...userInfos,
            lines: [
                {
                    ...userInfos.lines[0],
                    product: [1, "Big Plate", "9.9", 4.95],
                    quantity: 2,
                    price: 4.95 * 2,
                },
            ],
            total: 4.95 * 2,
            unpaid_subtotal: 4.95 * 2,
        };

        return true;
    });
    await mountLunchView();

    await contains("div.o_lunch_banner > .row > div:nth-child(2) span.fa-plus-circle").click();
});

test("Confirm existing order", async () => {
    expect.assertions(3);

    let userInfos = {
        ...lunchInfos,
        lines: [
            {
                id: 1,
                product: [1, "Big Plate", "4.95", 4.95],
                toppings: [],
                quantity: 1,
                price: 4.95,
                raw_state: "new",
                state: "To Order",
                note: false,
            },
        ],
        raw_state: "new",
        total: "4.95",
        paid_subtotal: "0",
        unpaid_subtotal: "4.95",
    };
    onRpc("/lunch/user_location_get", () => userInfos.user_location[0]);
    onRpc("/lunch/infos", () => userInfos);
    onRpc("/lunch/pay", async (request) => {
        const { params } = await request.json();
        expect(params.user_id).toBe(false); // Should confirm order of current user
        userInfos = {
            ...userInfos,
            lines: [
                {
                    ...userInfos.lines[0],
                    raw_state: "ordered",
                    state: "Ordered,",
                },
            ],
            raw_state: "ordered",
            wallet: userInfos.wallet - 4.95,
        };
        return true;
    });
    await mountLunchView();
    expect(".o_lunch_banner .w-100 > .d-flex > span:nth-child(2)").toHaveText("12.05\n€");

    await contains("div.o_lunch_banner > .row > div:nth-child(3) button").click();

    expect(".o_lunch_banner .w-100 > .d-flex > span:nth-child(2)").toHaveText("7.10\n€", {
        message: "Wallet should update",
    });
});
