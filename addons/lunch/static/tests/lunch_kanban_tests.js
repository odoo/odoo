/** @odoo-module */

import { click, getFixture, nextTick, patchWithCleanup } from '@web/../tests/helpers/utils';
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

import { LunchKanbanRenderer } from '@lunch/views/kanban';

let target;
let serverData;
let lunchInfos;

async function makeLunchView(extraArgs = {}) {
    return await makeView(
        Object.assign({
            serverData,
            type: "kanban",
            resModel: "lunch.product",
            arch: `
            <kanban js_class="lunch_kanban">
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="name"/>
                            <field name="price"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
            mockRPC: (route, args) => {
                if (route == '/lunch/user_location_get') {
                    return Promise.resolve(serverData.models['lunch.location'].records[0].id);
                } else if (route == '/lunch/infos') {
                    return Promise.resolve(lunchInfos);
                }
            }
        }, extraArgs
    ));
}

QUnit.module('Lunch', {}, function() {
QUnit.module('LunchKanban', (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                'lunch.product': {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: 'Name', type: 'char' },
                        is_available_at: { string: 'Available', type: 'integer' },
                        price: { string: 'Price', type: 'float', },
                    },
                    records: [
                        { id: 1, name: "Big Plate", is_available_at: 1, price: 4.95, },
                        { id: 2, name: "Small Plate", is_available_at: 2, price: 6.99, },
                        { id: 3, name: "Just One Plate", is_available_at: 2, price: 5.87, },
                    ]
                },
                'lunch.location': {
                    fields: {
                        name: { string: 'Name', type: 'char' },
                    },
                    records: [
                        { id: 1, name: "Old Office" },
                        { id: 2, name: "New Office" },
                    ]
                },
                'lunch.order': {
                    fields: {
                        product_id: { string: 'Product', type: 'many2one', relation: 'lunch.product', },
                    }
                },
                'res.users': {
                    fields: {
                        share: { type: 'boolean', },
                    },
                    records: [
                        { id: 1, name: 'Johnny Hache', share: false, },
                        { id: 2, name: 'David Elora', share: false, }
                    ]
                }
            },
            views: {
                'lunch.order,false,form': `<form>
                        <sheet>
                            <field name="product_id" readonly="1"/>
                        </sheet>
                        <footer>
                            <button name="add_to_cart" type="object" string="Add to cart" />
                            <button string="Discard" special="cancel"/>
                        </footer>
                    </form>`
            }
        };
        lunchInfos = {
            username: "Johnny Hache",
            wallet: 12.05,
            is_manager: false,
            currency: {
                symbol: "€",
                position: "after",
            },
            user_location: [1, "Old Office"],
            alerts: [],
            lines: [],
        };

        setupViewRegistries();
    });

    QUnit.test("Basic rendering", async function (assert) {
        assert.expect(4);

        await makeLunchView();

        assert.containsOnce(target, '.o_lunch_banner');
        assert.containsNone(target, '.o_lunch_content .alert');
        assert.containsOnce(target, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        const lunchDashboard = target.querySelector('.o_lunch_banner');
        const lunchUser = lunchDashboard.querySelector('.lunch_user span');
        assert.equal(lunchUser.innerText, 'Johnny Hache');
    });

    QUnit.test("Open product", async function (assert) {
        assert.expect(2);

        await makeLunchView();

        patchWithCleanup(LunchKanbanRenderer.prototype, {
            openOrderLine(productId, orderId) {
                assert.equal(productId, 1);
            }
        });

        assert.containsOnce(target, '.o_kanban_record:not(.o_kanban_ghost)');

        click(target, '.o_kanban_record:not(.o_kanban_ghost)');
    });

    QUnit.test("Basic rendering with alerts", async function (assert) {
        assert.expect(2);

        let userInfos = {
            ...lunchInfos,
            alerts: [
                {
                    id: 1,
                    message: '<b>free boudin compote for everyone</b>',
                }
            ]
        };
        await makeLunchView({
            mockRPC: (route, args) => {
                if (route == '/lunch/user_location_get') {
                    return Promise.resolve(userInfos.user_location[0]);
                } else if (route == '/lunch/infos') {
                    return Promise.resolve(userInfos);
                }
            }
        });

        assert.containsOnce(target, '.o_lunch_content .alert');
        assert.equal(target.querySelector('.o_lunch_content .alert').innerText, 'free boudin compote for everyone');
    });

    QUnit.test("Open product", async function (assert) {
        assert.expect(2);

        await makeLunchView();

        patchWithCleanup(LunchKanbanRenderer.prototype, {
            openOrderLine(productId, orderId) {
                assert.equal(productId, 1);
            }
        });

        assert.containsOnce(target, '.o_kanban_record:not(.o_kanban_ghost)');

        click(target, '.o_kanban_record:not(.o_kanban_ghost)');
    });

    QUnit.test("Location change", async function (assert) {
        assert.expect(3);

        let userInfos = { ...lunchInfos };
        await makeLunchView({
            mockRPC: (route, args) => {
                if (route == '/lunch/user_location_get') {
                    return Promise.resolve(userInfos.user_location[0]);
                } else if (route == '/lunch/infos') {
                    return Promise.resolve(userInfos);
                } else if (route == '/lunch/user_location_set') {
                    assert.equal(args.location_id, 2);
                    userInfos.user_location = [2, "New Office"];
                    return Promise.resolve(true);
                }
            }
        });

        click(target, '.lunch_location input');

        await nextTick();
        assert.containsOnce(target, '.lunch_location .dropdown-item:contains(New Office)');

        click(target, '.lunch_location .dropdown-item:not(.ui-state-active)');

        await nextTick();
        assert.containsN(target, 'div[role=article].o_kanban_record', 2);
    });

    QUnit.test("Manager: user change", async function (assert) {
        assert.expect(8);

        let userInfos = { ...lunchInfos, is_manager: true };
        let expectedUserId = false; // false as we are requesting for the current user
        await makeLunchView({
            mockRPC: (route, args) => {
                if (route == '/lunch/user_location_get') {
                    return Promise.resolve(userInfos.user_location[0]);
                } else if (route == '/lunch/infos') {
                    assert.equal(expectedUserId, args.user_id);

                    if (expectedUserId === 2) {
                        userInfos = {
                            ...userInfos,
                            username: 'David Elora',
                            wallet: -10000,
                        };
                    }

                    return Promise.resolve(userInfos);
                } else if (route == '/lunch/user_location_set') {
                    assert.equal(args.location_id, 2);
                    userInfos.user_location = [2, "New Office"];
                    return Promise.resolve(true);
                }
            }
        });

        assert.containsOnce(target, '.lunch_user input');
        click(target, '.lunch_user input');

        await nextTick();
        assert.containsOnce(target, '.lunch_user .dropdown-item:contains(David Elora)');

        expectedUserId = 2;
        click(target, '.lunch_user .dropdown-item:not(.ui-state-active)');

        await nextTick();
        const wallet = target.querySelector('.o_lunch_banner .col-9 > .d-flex > span:nth-child(2)');
        assert.equal(wallet.innerText, '-10000.00€', 'David Elora is poor')

        click(target, '.lunch_location input');
        await nextTick();
        click(target, '.lunch_location .dropdown-item:not(.ui-state-active)');

        await nextTick();
        const user = target.querySelector('.lunch_user input');
        assert.equal(user.value, 'David Elora', 'changing location should not reset user');
    });

    QUnit.test("Trash existing order", async function (assert) {
        assert.expect(5);

        let userInfos = {
            ...lunchInfos,
            lines: [
                {
                    id: 1,
                    product: [1, "Big Plate", "4.95"],
                    toppings: [],
                    quantity: 1,
                    price: 4.95,
                    raw_state: "new",
                    state: "To Order",
                    note: false
                }
            ],
            raw_state: "new",
            total: "4.95",
        };
        await makeLunchView({
            mockRPC: (route, args) => {
                if (route == '/lunch/user_location_get') {
                    return Promise.resolve(userInfos.user_location[0]);
                } else if (route == '/lunch/infos') {
                    return Promise.resolve(userInfos);
                } else if (route == '/lunch/trash') {
                    userInfos = {
                        ...userInfos,
                        lines: [],
                        raw_state: false,
                        total: 0,
                    };
                    return Promise.resolve(true);
                }
            }
        });

        assert.containsN(target, 'div.o_lunch_banner > .row > div', 3);
        assert.containsOnce(target, 'div.o_lunch_banner > .row > div:nth-child(2) button.fa-trash', 'should have trash icon');
        assert.containsOnce(target, 'div.o_lunch_banner > .row > div:nth-child(2) ul > li', 'should have one order line');

        assert.containsOnce(target, 'div.o_lunch_banner > .row > div:nth-child(3) button:contains(Order Now)');

        click(target, 'div.o_lunch_banner > .row > div:nth-child(2) button.fa-trash');
        await nextTick();
        assert.containsN(target, 'div.o_lunch_banner > .row > div', 1);
    });

    QUnit.test("Change existing order", async function (assert) {
        assert.expect(1);

        let userInfos = {
            ...lunchInfos,
            lines: [
                {
                    id: 1,
                    product: [1, "Big Plate", "4.95"],
                    toppings: [],
                    quantity: 1,
                    price: 4.95,
                    raw_state: "new",
                    state: "To Order",
                    note: false
                }
            ],
            raw_state: "new",
            total: "4.95",
        };
        await makeLunchView({
            mockRPC: (route, args) => {
                if (route == '/lunch/user_location_get') {
                    return Promise.resolve(userInfos.user_location[0]);
                } else if (route == '/lunch/infos') {
                    return Promise.resolve(userInfos);
                } else if (route == '/web/dataset/call_kw/lunch.order/update_quantity') {
                    assert.equal(args.args[1], 1, 'should increment order quantity by 1');
                    userInfos = {
                        ...userInfos,
                        lines: [
                            {
                                ...userInfos.lines[0],
                                product: [1, "Big Plate", "9.9"],
                                quantity: 2,
                                price: 4.95 * 2,
                            }
                        ],
                        total: 4.95 * 2,
                    };

                    return Promise.resolve(true);
                }
            }
        });

        click(target, 'div.o_lunch_banner > .row > div:nth-child(2) button.fa-plus-circle');
    });

    QUnit.test("Confirm existing order", async function (assert) {
        assert.expect(3);

        let userInfos = {
            ...lunchInfos,
            lines: [
                {
                    id: 1,
                    product: [1, "Big Plate", "4.95"],
                    toppings: [],
                    quantity: 1,
                    price: 4.95,
                    raw_state: "new",
                    state: "To Order",
                    note: false
                }
            ],
            raw_state: "new",
            total: "4.95",
        };
        await makeLunchView({
            mockRPC: (route, args) => {
                if (route == '/lunch/user_location_get') {
                    return Promise.resolve(userInfos.user_location[0]);
                } else if (route == '/lunch/infos') {
                    return Promise.resolve(userInfos);
                } else if (route == '/lunch/pay') {
                    assert.equal(args.user_id, false); // Should confirm order of current user
                    userInfos = {
                        ...userInfos,
                        lines: [
                            {
                                ...userInfos.lines[0],
                                raw_state: 'ordered',
                                state: 'Ordered,'
                            }
                        ],
                        raw_state: 'ordered',
                        wallet: userInfos.wallet - 4.95,
                    };
                    return Promise.resolve(true);
                }
            }
        });

        const wallet = target.querySelector('.o_lunch_banner .col-9 > .d-flex > span:nth-child(2)');
        assert.equal(wallet.innerText, '12.05€');

        click(target, 'div.o_lunch_banner > .row > div:nth-child(3) button');

        await nextTick();
        assert.equal(wallet.innerText, '7.10€', 'Wallet should update');
    });
});
});
