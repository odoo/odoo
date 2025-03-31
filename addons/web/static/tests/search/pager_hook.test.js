import { expect, test } from "@odoo/hoot";
import { Component, useState, xml } from "@odoo/owl";
import {
    defineModels,
    getPagerLimit,
    getPagerValue,
    models,
    mountWithSearch,
    pagerNext,
} from "@web/../tests/web_test_helpers";

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { usePager } from "@web/search/pager_hook";
import { animationFrame } from "@odoo/hoot-mock";

class Foo extends models.Model {
    _views = {
        search: `<search/>`,
    };
}
defineModels([Foo]);

test("pager is correctly displayed", async () => {
    class TestComponent extends Component {
        static components = { ControlPanel };
        static template = xml`<ControlPanel />`;
        static props = ["*"];
        setup() {
            usePager(() => ({
                offset: 0,
                limit: 10,
                total: 50,
                onUpdate: () => {},
            }));
        }
    }

    await mountWithSearch(TestComponent, {
        resModel: "foo",
        searchMenuTypes: [],
    });
    expect(`.o_pager`).toHaveCount(1);
    expect(".o_pager button.o_pager_next").toHaveCount(1);
    expect(".o_pager button.o_pager_previous").toHaveCount(1);
});

test.tags("desktop");
test("pager is correctly displayed on desktop", async () => {
    class TestComponent extends Component {
        static components = { ControlPanel };
        static template = xml`<ControlPanel />`;
        static props = ["*"];
        setup() {
            usePager(() => ({
                offset: 0,
                limit: 10,
                total: 50,
                onUpdate: () => {},
            }));
        }
    }

    await mountWithSearch(TestComponent, {
        resModel: "foo",
        searchMenuTypes: [],
    });
    expect(`.o_pager`).toHaveCount(1);
    expect(getPagerValue()).toEqual([1, 10]);
    expect(getPagerLimit()).toBe(50);
});

test("pager is correctly updated", async () => {
    class TestComponent extends Component {
        static components = { ControlPanel };
        static template = xml`<ControlPanel />`;
        static props = ["*"];
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

    const component = await mountWithSearch(TestComponent, {
        resModel: "foo",
        searchMenuTypes: [],
    });
    expect(`.o_pager`).toHaveCount(1);
    expect(component.state).toEqual({ offset: 0, limit: 10 });

    await pagerNext();
    expect(`.o_pager`).toHaveCount(1);
    expect(component.state).toEqual({ offset: 10, limit: 10 });

    component.state.offset = 20;
    await animationFrame();
    expect(`.o_pager`).toHaveCount(1);
    expect(component.state).toEqual({ offset: 20, limit: 10 });
});

test.tags("desktop");
test("pager is correctly updated on desktop", async () => {
    class TestComponent extends Component {
        static components = { ControlPanel };
        static template = xml`<ControlPanel />`;
        static props = ["*"];
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

    const component = await mountWithSearch(TestComponent, {
        resModel: "foo",
        searchMenuTypes: [],
    });
    expect(`.o_pager`).toHaveCount(1);
    expect(getPagerValue()).toEqual([1, 10]);
    expect(getPagerLimit()).toBe(50);

    await pagerNext();
    expect(`.o_pager`).toHaveCount(1);
    expect(getPagerValue()).toEqual([11, 20]);
    expect(getPagerLimit()).toBe(50);

    component.state.offset = 20;
    await animationFrame();
    expect(`.o_pager`).toHaveCount(1);
    expect(getPagerValue()).toEqual([21, 30]);
    expect(getPagerLimit()).toBe(50);
});
