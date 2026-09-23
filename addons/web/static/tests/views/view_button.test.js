// @ts-check

import "@web/views/form/form_utils";
import "@web/views/view_utils";

import { expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { Component, useRef, useState, xml } from "@odoo/owl";
import {
    contains,
    mockService,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { MultiRecordViewButton } from "@web/views/view_button/multi_record_view_button";
import { ViewButton } from "@web/views/view_button/view_button";
import { useViewButtons } from "@web/views/view_button/view_button_hook";

/** @param {string} buttonXml */
async function mountButton(buttonXml) {
    class Parent extends Component {
        static components = { ViewButton, MultiRecordViewButton };
        static props = ["*"];
        static template = xml`<div t-ref="root">${buttonXml}</div>`;
        setup() {
            useViewButtons(useRef("root"));
        }
    }
    await mountWithCleanup(Parent);
}

test("getClassName: oe_highlight legacy class maps to btn-primary", async () => {
    await mountButton(
        `<ViewButton className="'oe_highlight'" string="'X'" clickParams="{ type: 'object' }"/>`,
    );
    expect("button").toHaveClass(["btn", "btn-primary"]);
    expect("button").not.toHaveClass("btn-secondary");
});

test("getClassName: empty class + defaultRank applies that rank", async () => {
    await mountButton(
        `<ViewButton className="''" defaultRank="'btn-primary'" string="'X'" clickParams="{ type: 'object' }"/>`,
    );
    expect("button").toHaveClass(["btn", "btn-primary"]);
});

test("getClassName: empty class + no rank falls back to btn-secondary", async () => {
    await mountButton(
        `<ViewButton className="''" string="'X'" clickParams="{ type: 'object' }"/>`,
    );
    expect("button").toHaveClass(["btn", "btn-secondary"]);
});

test("getClassName: a custom non-rank class does NOT get btn-secondary", async () => {
    await mountButton(
        `<ViewButton className="'my-class'" string="'X'" clickParams="{ type: 'object' }"/>`,
    );
    expect("button").toHaveClass(["btn", "my-class"]);
    expect("button").not.toHaveClass("btn-secondary");
});

test("getClassName: size adds btn-<size>", async () => {
    await mountButton(
        `<ViewButton className="''" size="'sm'" string="'X'" clickParams="{ type: 'object' }"/>`,
    );
    expect("button").toHaveClass("btn-sm");
});

test("iconFromString: FA4 bare name normalizes to fa-solid", async () => {
    await mountButton(
        `<ViewButton icon="'fa-edit'" clickParams="{ type: 'object' }"/>`,
    );
    expect("button i.o_button_icon").toHaveClass(["fa-solid", "fa-edit"]);
});

test("iconFromString: FA4 outline -o maps to fa-regular and strips -o", async () => {
    await mountButton(
        `<ViewButton icon="'fa-star-o'" clickParams="{ type: 'object' }"/>`,
    );
    expect("button i.o_button_icon").toHaveClass(["fa-regular", "fa-star"]);
    expect("button i.o_button_icon").not.toHaveClass("fa-star-o");
});

test("iconFromString: odoo icon oi- prefix", async () => {
    await mountButton(
        `<ViewButton icon="'oi-settings'" clickParams="{ type: 'object' }"/>`,
    );
    expect("button i.o_button_icon").toHaveClass(["oi", "oi-fw", "oi-settings"]);
});

test("iconFromString: a non-icon string renders an <img>", async () => {
    await mountButton(
        `<ViewButton icon="'/web/static/img/x.png'" clickParams="{ type: 'object' }"/>`,
    );
    expect("button img").toHaveAttribute("src", "/web/static/img/x.png");
});

test("tooltip (P1): without help/debug there is no tooltip template attribute", async () => {
    await mountButton(`<ViewButton string="'X'" clickParams="{ type: 'object' }"/>`);
    expect("button").not.toHaveAttribute("data-tooltip-template");
});

test("tooltip (P1): help text activates the lazy tooltip getter", async () => {
    await mountButton(
        `<ViewButton string="'X'" clickParams="{ type: 'object', help: 'Helpful' }"/>`,
    );
    expect("button").toHaveAttribute(
        "data-tooltip-template",
        "views.ViewButtonTooltip",
    );
});

test("MultiRecordViewButton (L1): does not mutate the shared clickParams object", async () => {
    mockService("action", { async doActionButton() {} });
    const clickParams = { type: "object", name: "act" };
    class Parent extends Component {
        static components = { MultiRecordViewButton };
        static props = ["*"];
        static template = xml`
            <div t-ref="root">
                <MultiRecordViewButton list="this.list" domain="[]" clickParams="this.clickParams" string="'Go'"/>
            </div>`;
        setup() {
            useViewButtons(useRef("root"));
            this.clickParams = clickParams;
            this.list = {
                getResIds: async () => [1, 2],
                resModel: "res.partner",
                context: {},
                evalContext: {},
            };
        }
    }
    await mountWithCleanup(Parent);
    await contains("button").click();
    await animationFrame();
    expect("buttonContext" in clickParams).toBe(false);
});

test("prop shape (M1): accepts the union types real call sites pass", async () => {
    await mountButton(
        `<ViewButton id="42" icon="false" context="{ foo: 1 }" tabindex="'-1'" record="{ resId: 1 }" string="'X'" clickParams="{ type: 'object' }"/>`,
    );
    expect("button").toHaveCount(1);
    expect("button i").toHaveCount(0);
});

test("shared_components (M2): validation schema installed; every entry is callable", () => {
    const shared = registry.category("shared_components");
    expect(typeof shared.validationSchema).toBe("function");
    expect(shared.validationSchema(function () {})).toBe(true);
    expect(shared.validationSchema({})).toBe(false);
    for (const key of [
        "ViewButton",
        "executeButtonCallback",
        "useViewButtons",
        "computeViewClassName",
        "loadSubViews",
        "useFormViewInDialog",
    ]) {
        expect(shared.validationSchema(shared.get(key))).toBe(true);
    }
});

test("R2 probe: an OWL re-render of the button mid-action keeps it disabled", async () => {
    const def = new Deferred();
    mockService("action", {
        async doActionButton() {
            return def;
        },
    });

    /** @type {Parent} */
    let parent;
    class Parent extends Component {
        static components = { ViewButton };
        static props = ["*"];
        static template = xml`
            <div t-ref="root">
                <ViewButton string="this.state.label" clickParams="{ type: 'object', name: 'act' }" record="{ resId: 1 }"/>
            </div>`;
        setup() {
            parent = this;
            this.state = useState({ label: "Go" });
            useViewButtons(useRef("root"));
        }
    }
    await mountWithCleanup(Parent);

    await contains("button").click();
    expect("button").toHaveAttribute("disabled");

    parent.state.label = "Running";
    await animationFrame();
    expect("button").toHaveText("Running");

    expect("button").toHaveAttribute("disabled");

    def.resolve();
    await animationFrame();
    expect("button").not.toHaveAttribute("disabled");
});
