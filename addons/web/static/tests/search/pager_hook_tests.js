/** @odoo-module **/

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { usePager } from "@web/search/pager_hook";
import { click, getFixture, nextTick } from "../helpers/utils";
import { makeWithSearch, setupControlPanelServiceRegistry } from "./helpers";

const { Component, useState, xml } = owl;

let target;
let serverData;
QUnit.module("Search", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                foo: {
                    fields: {},
                },
            },
            views: {
                "foo,false,search": `<search/>`,
            },
        };
        setupControlPanelServiceRegistry();
        target = getFixture();
    });

    QUnit.module("usePager");

    QUnit.test("pager is correctly displayed", async (assert) => {
        class TestComponent extends Component {
            setup() {
                usePager(() => ({
                    offset: 0,
                    limit: 10,
                    total: 50,
                    onUpdate: () => {},
                }));
            }
        }
        TestComponent.components = { ControlPanel };
        TestComponent.template = xml`<ControlPanel />`;

        await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: TestComponent,
            searchMenuTypes: [],
        });

        assert.containsOnce(target, ".o_pager");
        assert.strictEqual(
            target.querySelector(`.o_pager_counter .o_pager_value`).textContent.trim(),
            "1-10"
        );
        assert.strictEqual(
            target.querySelector(`.o_pager_counter span.o_pager_limit`).textContent.trim(),
            "50"
        );
    });

    QUnit.test("pager is correctly updated", async (assert) => {
        class TestComponent extends Component {
            setup() {
                this.state = useState({ offset: 0, limit: 10 });
                usePager(() => ({
                    offset: this.state.offset,
                    limit: this.state.limit,
                    total: 50,
                    onUpdate: (newState) => {
                        Object.assign(this.state, newState);
                    },
                }));
            }
        }
        TestComponent.components = { ControlPanel };
        TestComponent.template = xml`<ControlPanel />`;

        const comp = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: TestComponent,
            searchMenuTypes: [],
        });

        assert.containsOnce(target, ".o_pager");
        assert.strictEqual(
            target.querySelector(`.o_pager_counter .o_pager_value`).textContent.trim(),
            "1-10"
        );
        assert.strictEqual(
            target.querySelector(`.o_pager_counter span.o_pager_limit`).textContent.trim(),
            "50"
        );
        assert.deepEqual(comp.state, {
            offset: 0,
            limit: 10,
        });

        await click(target.querySelector(`.o_pager button.o_pager_next`));

        assert.containsOnce(target, ".o_pager");
        assert.strictEqual(
            target.querySelector(`.o_pager_counter .o_pager_value`).textContent.trim(),
            "11-20"
        );
        assert.strictEqual(
            target.querySelector(`.o_pager_counter span.o_pager_limit`).textContent.trim(),
            "50"
        );
        assert.deepEqual(comp.state, {
            offset: 10,
            limit: 10,
        });

        comp.state.offset = 20;
        await nextTick();

        assert.containsOnce(target, ".o_pager");
        assert.strictEqual(
            target.querySelector(`.o_pager_counter .o_pager_value`).textContent.trim(),
            "21-30"
        );
        assert.strictEqual(
            target.querySelector(`.o_pager_counter span.o_pager_limit`).textContent.trim(),
            "50"
        );
        assert.deepEqual(comp.state, {
            offset: 20,
            limit: 10,
        });
    });
});
