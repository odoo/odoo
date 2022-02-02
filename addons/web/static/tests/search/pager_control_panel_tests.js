/** @odoo-module **/

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { click, nextTick } from "../helpers/utils";
import { makeWithSearch, setupControlPanelServiceRegistry } from "./helpers";
import { Layout } from "@web/views/layout";

const { Component, useState, xml } = owl;

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
    });

    QUnit.module("Pager on ControlPanel");

    QUnit.test("pager is correctly displayed", async (assert) => {
        class TestComponent extends Component {
            get pagerProps() {
                return {
                    offset: 0,
                    limit: 10,
                    total: 50,
                    onUpdate: () => {},
                };
            }
        }
        TestComponent.components = { ControlPanel };
        TestComponent.template = xml`<ControlPanel pagerProps="pagerProps" />`;

        const comp = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: TestComponent,
            searchMenuTypes: [],
        });

        assert.containsOnce(comp, ".o_pager");
        assert.strictEqual(
            comp.el.querySelector(`.o_pager_counter .o_pager_value`).textContent.trim(),
            "1-10"
        );
        assert.strictEqual(
            comp.el.querySelector(`.o_pager_counter span.o_pager_limit`).textContent.trim(),
            "50"
        );
    });

    QUnit.test("pager is correctly updated", async (assert) => {
        class TestComponent extends Component {
            setup() {
                this.state = useState({ offset: 0, limit: 10 });
            }

            get pagerProps() {
                return {
                    offset: this.state.offset,
                    limit: this.state.limit,
                    total: 50,
                    onUpdate: (newState) => {
                        Object.assign(this.state, newState);
                    },
                };
            }
        }
        TestComponent.components = { Layout };
        TestComponent.template = xml`<Layout pagerProps="pagerProps" />`;

        const comp = await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: TestComponent,
            searchMenuTypes: [],
        });

        assert.containsOnce(comp, ".o_pager");
        assert.strictEqual(
            comp.el.querySelector(`.o_pager_counter .o_pager_value`).textContent.trim(),
            "1-10"
        );
        assert.strictEqual(
            comp.el.querySelector(`.o_pager_counter span.o_pager_limit`).textContent.trim(),
            "50"
        );
        assert.deepEqual(comp.state, {
            offset: 0,
            limit: 10,
        });

        //Change the offset by cliking on the "next" button
        await click(comp.el.querySelector(`.o_pager button.o_pager_next`));

        assert.containsOnce(comp, ".o_pager");
        assert.strictEqual(
            comp.el.querySelector(`.o_pager_counter .o_pager_value`).textContent.trim(),
            "11-20"
        );
        assert.strictEqual(
            comp.el.querySelector(`.o_pager_counter span.o_pager_limit`).textContent.trim(),
            "50"
        );
        assert.deepEqual(comp.state, {
            offset: 10,
            limit: 10,
        });

        //Change the offset by code
        comp.state.offset = 20;
        await nextTick();

        assert.containsOnce(comp, ".o_pager");
        assert.strictEqual(
            comp.el.querySelector(`.o_pager_counter .o_pager_value`).textContent.trim(),
            "21-30"
        );
        assert.strictEqual(
            comp.el.querySelector(`.o_pager_counter span.o_pager_limit`).textContent.trim(),
            "50"
        );
        assert.deepEqual(comp.state, {
            offset: 20,
            limit: 10,
        });
    });
});
