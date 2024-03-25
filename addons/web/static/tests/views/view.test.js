import { Component, onWillStart, onWillUpdateProps, useState, xml } from "@odoo/owl";
import { CallbackRecorder } from "@web/webclient/actions/action_hook";
import { OnboardingBanner } from "@web/views/onboarding_banner";
import { pick } from "@web/core/utils/objects";
import { registry } from "@web/core/registry";
import { View } from "@web/views/view";

import { expect, test } from "@odoo/hoot";
import { click, queryOne } from "@odoo/hoot-dom";
import { Deferred, animationFrame, runAllTimers } from "@odoo/hoot-mock";
import {
    defineModels,
    fields,
    makeMockEnv,
    mockService,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

const viewRegistry = registry.category("views");

class ToyController extends Component {
    static props = ["*"];
    static template = xml`<div t-attf-class="{{class}} {{props.className}}"><t t-call="{{ template }}"/></div>`;
    static components = { Banner: OnboardingBanner };
    setup() {
        this.class = "toy";
        this.template = xml`${this.props.arch.outerHTML}`;
    }
}

const toyView = {
    type: "toy",
    Controller: ToyController,
};

class ToyControllerImp extends ToyController {
    setup() {
        super.setup();
        this.class = "toy_imp";
    }
}

viewRegistry.add("toy", toyView);
viewRegistry.add("toy_imp", { ...toyView, Controller: ToyControllerImp });

class Animal extends models.Model {
    birthday = fields.Date();
    type = fields.Selection({
        selection: [
            ["omnivorous", "Omnivorous"],
            ["herbivorous", "Herbivorous"],
            ["carnivorous", "Carnivorous"],
        ],
        default: "red",
    });

    _views = {
        toy: /* xml */ `<toy>Arch content (id=false)</toy>`,
        "toy,1": /* xml */ `<toy>Arch content (id=1)</toy>`,
        "toy,2": /* xml */ `<toy js_class="toy_imp">Arch content (id=2)</toy>`,
        other: /* xml */ `<other/>`,
        search: /* xml */ `<search/>`,
        "search,1": /* xml */ `
            <search>
                <filter name="filter" domain="[(1, '=', 1)]"/>
                <filter name="group_by" context="{ 'group_by': 'display_name' }"/>
            </search>
        `,
    };

    _filters = [
        {
            context: "{}",
            domain: "[('animal', 'ilike', 'o')]",
            id: 7,
            is_default: true,
            name: "My favorite",
            sort: "[]",
            user_id: [2, "Mitchell Admin"],
        },
    ];
}

defineModels([Animal]);

////////////////////////////////////////////////////////////////////////////
// get_views
////////////////////////////////////////////////////////////////////////////

test("simple rendering", async function () {
    expect.assertions(9);
    patchWithCleanup(ToyController.prototype, {
        setup() {
            super.setup();
            const { arch, fields, info } = this.props;
            expect(arch.outerHTML).toBe(`<toy>Arch content (id=false)</toy>`);
            expect(fields).toEqual({});
            expect(info.actionMenus).toBe(undefined);
            expect(this.env.config.viewId).toBe(false);
        },
    });
    onRpc("get_views", (_, { model, kwargs }) => {
        expect(model).toBe("animal");
        expect(kwargs.views).toEqual([[false, "toy"]]);
        expect(pick(kwargs.options, "action_id", "load_filters", "toolbar")).toEqual({
            action_id: false,
            load_filters: false,
            toolbar: false,
        });
    });
    await mountWithCleanup(View, { props: { resModel: "animal", type: "toy" } });
    expect(".o_toy_view.o_view_controller").toHaveCount(1);
    expect(queryOne(".o_toy_view.toy").innerHTML).toBe(`<toy>Arch content (id=false)</toy>`);
});

test("rendering with given viewId", async function () {
    expect.assertions(8);
    patchWithCleanup(ToyController.prototype, {
        setup() {
            super.setup();
            const { arch, fields, info } = this.props;
            expect(arch.outerHTML).toBe(`<toy>Arch content (id=1)</toy>`);
            expect(fields).toEqual({});
            expect(info.actionMenus).toBe(undefined);
            expect(this.env.config.viewId).toBe(1);
        },
    });
    onRpc("get_views", (_, { kwargs }) => {
        expect(kwargs.views).toEqual([[1, "toy"]]);
        expect(pick(kwargs.options, "action_id", "load_filters", "toolbar")).toEqual({
            action_id: false,
            load_filters: false,
            toolbar: false,
        });
    });
    await mountWithCleanup(View, { props: { resModel: "animal", type: "toy", viewId: 1 } });
    expect(".o_toy_view.o_view_controller").toHaveCount(1);
    expect(queryOne(".o_toy_view.toy").innerHTML).toBe(`<toy>Arch content (id=1)</toy>`);
});

test("rendering with given 'views' param", async function () {
    expect.assertions(8);
    patchWithCleanup(ToyController.prototype, {
        setup() {
            super.setup();
            const { arch, fields, info } = this.props;
            expect(arch.outerHTML).toBe(`<toy>Arch content (id=1)</toy>`);
            expect(fields).toEqual({});
            expect(info.actionMenus).toBe(undefined);
            expect(this.env.config.viewId).toBe(1);
        },
    });
    onRpc("get_views", (_, { kwargs }) => {
        expect(kwargs.views).toEqual([[1, "toy"]]);
        expect(pick(kwargs.options, "action_id", "load_filters", "toolbar")).toEqual({
            action_id: false,
            load_filters: false,
            toolbar: false,
        });
    });
    const env = await makeMockEnv({ config: { views: [[1, "toy"]] } });
    await mountWithCleanup(View, { props: { resModel: "animal", type: "toy" }, env });
    expect(".o_toy_view.o_view_controller").toHaveCount(1);
    expect(queryOne(".o_toy_view.toy").innerHTML).toBe(`<toy>Arch content (id=1)</toy>`);
});

test("rendering with given 'views' param not containing view id", async function () {
    expect.assertions(8);
    patchWithCleanup(ToyController.prototype, {
        setup() {
            super.setup();
            const { arch, fields, info } = this.props;
            expect(arch.outerHTML).toBe(`<toy>Arch content (id=false)</toy>`);
            expect(fields).toEqual({});
            expect(info.actionMenus).toBe(undefined);
            expect(this.env.config.viewId).toBe(false);
        },
    });
    onRpc("get_views", (_, { kwargs }) => {
        expect(kwargs.views).toEqual([
            [false, "other"],
            [false, "toy"],
        ]);
        expect(pick(kwargs.options, "action_id", "load_filters", "toolbar")).toEqual({
            action_id: false,
            load_filters: false,
            toolbar: false,
        });
    });
    const env = await makeMockEnv({ config: { views: [[false, "other"]] } });
    await mountWithCleanup(View, { props: { resModel: "animal", type: "toy" }, env });
    expect(".o_toy_view.o_view_controller").toHaveCount(1);
    expect(queryOne(".o_toy_view.toy").innerHTML).toBe(`<toy>Arch content (id=false)</toy>`);
});

test("viewId defined as prop and in 'views' prop", async function () {
    expect.assertions(8);
    patchWithCleanup(ToyController.prototype, {
        setup() {
            super.setup();
            const { arch, fields, info } = this.props;
            expect(arch.outerHTML).toBe(`<toy>Arch content (id=1)</toy>`);
            expect(fields).toEqual({});
            expect(info.actionMenus).toBe(undefined);
            expect(this.env.config.viewId).toBe(1);
        },
    });
    onRpc("get_views", (_, { kwargs }) => {
        expect(kwargs.views).toEqual([
            [1, "toy"],
            [false, "other"],
        ]);
        expect(pick(kwargs.options, "action_id", "load_filters", "toolbar")).toEqual({
            action_id: false,
            load_filters: false,
            toolbar: false,
        });
    });
    const env = await makeMockEnv({
        config: {
            views: [
                [3, "toy"],
                [false, "other"],
            ],
        },
    });
    await mountWithCleanup(View, { props: { resModel: "animal", type: "toy", viewId: 1 }, env });
    expect(".o_toy_view.o_view_controller").toHaveCount(1);
    expect(queryOne(".o_toy_view.toy").innerHTML).toBe(`<toy>Arch content (id=1)</toy>`);
});

test("rendering with given arch and fields", async function () {
    expect.assertions(6);
    patchWithCleanup(ToyController.prototype, {
        setup() {
            super.setup();
            const { arch, fields, info } = this.props;
            expect(arch.outerHTML).toBe(`<toy>Specific arch content</toy>`);
            expect(fields).toEqual({});
            expect(info.actionMenus).toBe(undefined);
            expect(this.env.config.viewId).toBe(undefined);
        },
    });
    onRpc("get_views", () => {
        throw new Error("no get_views expected");
    });
    await mountWithCleanup(View, {
        props: {
            resModel: "animal",
            type: "toy",
            arch: `<toy>Specific arch content</toy>`,
            fields: {},
        },
    });
    expect(".o_toy_view.o_view_controller").toHaveCount(1);
    expect(queryOne(".o_toy_view.toy").innerHTML).toBe(`<toy>Specific arch content</toy>`);
});

test("rendering with loadActionMenus='true'", async function () {
    expect.assertions(8);
    patchWithCleanup(ToyController.prototype, {
        setup() {
            super.setup();
            const { arch, fields, info } = this.props;
            expect(arch.outerHTML).toBe(`<toy>Arch content (id=false)</toy>`);
            expect(fields).toEqual({});
            expect(info.actionMenus).toEqual({});
            expect(this.env.config.viewId).toBe(false);
        },
    });
    onRpc("get_views", (_, { kwargs }) => {
        expect(kwargs.views).toEqual([[false, "toy"]]);
        expect(pick(kwargs.options, "action_id", "load_filters", "toolbar")).toEqual({
            action_id: false,
            load_filters: false,
            toolbar: true,
        });
    });
    await mountWithCleanup(View, {
        props: { resModel: "animal", type: "toy", loadActionMenus: true },
    });
    expect(".o_toy_view.o_view_controller").toHaveCount(1);
    expect(queryOne(".o_toy_view.toy").innerHTML).toBe(`<toy>Arch content (id=false)</toy>`);
});

test("rendering with given arch, fields, and loadActionMenus='true'", async function () {
    expect.assertions(8);
    patchWithCleanup(ToyController.prototype, {
        setup() {
            super.setup();
            const { arch, fields, info } = this.props;
            expect(arch.outerHTML).toBe(`<toy>Specific arch content</toy>`);
            expect(fields).toEqual({});
            expect(info.actionMenus).toEqual({});
            expect(this.env.config.viewId).toBe(false);
        },
    });
    onRpc("get_views", (_, { kwargs }) => {
        expect(kwargs.views).toEqual([[false, "toy"]]);
        expect(pick(kwargs.options, "action_id", "load_filters", "toolbar")).toEqual({
            action_id: false,
            load_filters: false,
            toolbar: true,
        });
    });
    await mountWithCleanup(View, {
        props: {
            resModel: "animal",
            type: "toy",
            arch: `<toy>Specific arch content</toy>`,
            fields: {},
            loadActionMenus: true,
        },
    });
    expect(".o_toy_view.o_view_controller").toHaveCount(1);
    expect(queryOne(".o_toy_view.toy").innerHTML).toBe(`<toy>Specific arch content</toy>`);
});

test("rendering with given arch, fields, actionMenus, and loadActionMenus='true'", async function () {
    expect.assertions(6);
    patchWithCleanup(ToyController.prototype, {
        setup() {
            super.setup();
            const { arch, fields, info } = this.props;
            expect(arch.outerHTML).toBe(`<toy>Specific arch content</toy>`);
            expect(fields).toEqual({});
            expect(info.actionMenus).toEqual({});
            expect(this.env.config.viewId).toBe(undefined);
        },
    });
    onRpc("get_views", () => {
        throw new Error("no get_views expected");
    });
    await mountWithCleanup(View, {
        props: {
            resModel: "animal",
            type: "toy",
            arch: `<toy>Specific arch content</toy>`,
            fields: {},
            loadActionMenus: true,
            actionMenus: {},
        },
    });
    expect(".o_toy_view.o_view_controller").toHaveCount(1);
    expect(queryOne(".o_toy_view.toy").innerHTML).toBe(`<toy>Specific arch content</toy>`);
});

test("rendering with given searchViewId", async function () {
    expect.assertions(8);
    patchWithCleanup(ToyController.prototype, {
        setup() {
            super.setup();
            const { irFilters, searchViewArch, searchViewFields, searchViewId } = this.props.info;
            expect(searchViewArch).toBe(`<search/>`);
            expect(searchViewFields).toEqual({
                id: {
                    string: "Id",
                    readonly: true,
                    required: false,
                    searchable: true,
                    sortable: true,
                    store: true,
                    groupable: true,
                    aggregator: "sum",
                    type: "integer",
                    name: "id",
                },
                display_name: {
                    string: "Display name",
                    readonly: true,
                    required: false,
                    searchable: true,
                    sortable: true,
                    store: false,
                    groupable: true,
                    type: "char",
                    compute: "_compute_display_name",
                    name: "display_name",
                },
                create_date: {
                    string: "Created on",
                    readonly: true,
                    required: false,
                    searchable: true,
                    sortable: true,
                    store: true,
                    groupable: true,
                    type: "datetime",
                    name: "create_date",
                },
                write_date: {
                    string: "Last Modified on",
                    readonly: true,
                    required: false,
                    searchable: true,
                    sortable: true,
                    store: true,
                    groupable: true,
                    type: "datetime",
                    name: "write_date",
                },
                birthday: {
                    string: "Birthday",
                    readonly: false,
                    required: false,
                    searchable: true,
                    sortable: true,
                    store: true,
                    groupable: true,
                    type: "date",
                    name: "birthday",
                },
                type: {
                    string: "Type",
                    readonly: false,
                    required: false,
                    searchable: true,
                    sortable: true,
                    store: true,
                    groupable: true,
                    type: "selection",
                    selection: [
                        ["omnivorous", "Omnivorous"],
                        ["herbivorous", "Herbivorous"],
                        ["carnivorous", "Carnivorous"],
                    ],
                    default: "red",
                    name: "type",
                },
            });
            expect(searchViewId).toBe(false);
            expect(irFilters).toBe(undefined);
        },
    });
    onRpc("get_views", (_, { kwargs }) => {
        expect(kwargs.views).toEqual([
            [false, "toy"],
            [false, "search"],
        ]);
        expect(pick(kwargs.options, "action_id", "load_filters", "toolbar")).toEqual({
            action_id: false,
            load_filters: false,
            toolbar: false,
        });
    });
    await mountWithCleanup(View, {
        props: { resModel: "animal", type: "toy", searchViewId: false },
    });
    expect(".o_toy_view.o_view_controller").toHaveCount(1);
    expect(queryOne(".o_toy_view.toy").innerHTML).toBe(`<toy>Arch content (id=false)</toy>`);
});

test("rendering with given arch, fields, searchViewId, searchViewArch, and searchViewFields", async function () {
    expect.assertions(6);
    patchWithCleanup(ToyController.prototype, {
        setup() {
            super.setup();
            const { irFilters, searchViewArch, searchViewFields, searchViewId } = this.props.info;
            expect(searchViewArch).toBe(`<search/>`);
            expect(searchViewFields).toEqual({});
            expect(searchViewId).toBe(false);
            expect(irFilters).toBe(undefined);
        },
    });
    onRpc("get_views", () => {
        throw new Error("no get_views expected");
    });
    await mountWithCleanup(View, {
        props: {
            resModel: "animal",
            type: "toy",
            arch: `<toy>Specific arch content</toy>`,
            fields: {},
            searchViewId: false,
            searchViewArch: `<search/>`,
            searchViewFields: {},
        },
    });
    expect(".o_toy_view.o_view_controller").toHaveCount(1);
    expect(queryOne(".o_toy_view.toy").innerHTML).toBe(`<toy>Specific arch content</toy>`);
});

test("rendering with given arch, fields, searchViewArch, and searchViewFields", async function () {
    expect.assertions(6);
    patchWithCleanup(ToyController.prototype, {
        setup() {
            super.setup();
            const { irFilters, searchViewArch, searchViewFields, searchViewId } = this.props.info;
            expect(searchViewArch).toBe(`<search/>`);
            expect(searchViewFields).toEqual({});
            expect(searchViewId).toBe(undefined);
            expect(irFilters).toBe(undefined);
        },
    });
    onRpc("get_views", () => {
        throw new Error("no get_views expected");
    });
    await mountWithCleanup(View, {
        props: {
            resModel: "animal",
            type: "toy",
            arch: `<toy>Specific arch content</toy>`,
            fields: {},
            searchViewArch: `<search/>`,
            searchViewFields: {},
        },
    });
    expect(".o_toy_view.o_view_controller").toHaveCount(1);
    expect(queryOne(".o_toy_view.toy").innerHTML).toBe(`<toy>Specific arch content</toy>`);
});

test("rendering with given arch, fields, searchViewId, searchViewArch, searchViewFields, and loadIrFilters='true'", async function () {
    expect.assertions(8);
    patchWithCleanup(ToyController.prototype, {
        setup() {
            super.setup();
            const { irFilters, searchViewArch, searchViewFields, searchViewId } = this.props.info;
            expect(searchViewArch).toBe(`<search/>`);
            expect(searchViewFields).toEqual({});
            expect(searchViewId).toBe(false);
            expect(irFilters).toEqual([
                {
                    context: "{}",
                    domain: "[('animal', 'ilike', 'o')]",
                    id: 7,
                    is_default: true,
                    name: "My favorite",
                    sort: "[]",
                    user_id: [2, "Mitchell Admin"],
                },
            ]);
        },
    });
    onRpc("get_views", (_, { kwargs }) => {
        expect(kwargs.views).toEqual([
            [false, "toy"],
            [false, "search"],
        ]);
        expect(pick(kwargs.options, "action_id", "load_filters", "toolbar")).toEqual({
            action_id: false,
            load_filters: true,
            toolbar: false,
        });
    });
    await mountWithCleanup(View, {
        props: {
            resModel: "animal",
            type: "toy",
            arch: `<toy>Specific arch content</toy>`,
            fields: {},
            searchViewId: false,
            searchViewArch: `<search/>`,
            searchViewFields: {},
            loadIrFilters: true,
        },
    });
    expect(".o_toy_view.o_view_controller").toHaveCount(1);
    expect(queryOne(".o_toy_view.toy").innerHTML).toBe(`<toy>Specific arch content</toy>`);
});

test("rendering with given arch, fields, searchViewId, searchViewArch, searchViewFields, irFilters, and loadIrFilters='true'", async function () {
    expect.assertions(6);
    const irFilters = [
        {
            context: "{}",
            domain: "[]",
            id: 1,
            is_default: false,
            name: "My favorite",
            sort: "[]",
            user_id: [2, "Mitchell Admin"],
        },
    ];
    patchWithCleanup(ToyController.prototype, {
        setup() {
            super.setup();
            const {
                irFilters: filters,
                searchViewArch,
                searchViewFields,
                searchViewId,
            } = this.props.info;
            expect(searchViewArch).toBe(`<search/>`);
            expect(searchViewFields).toEqual({});
            expect(searchViewId).toBe(undefined);
            expect(filters).toBe(irFilters); // irFilters is passed as it is without transformation -> we can use toBe instead of toEqual to avoid a warning
        },
    });
    onRpc("get_views", () => {
        throw new Error("no get_views expected");
    });
    await mountWithCleanup(View, {
        props: {
            resModel: "animal",
            type: "toy",
            arch: `<toy>Specific arch content</toy>`,
            fields: {},
            searchViewArch: `<search/>`,
            searchViewFields: {},
            loadIrFilters: true,
            irFilters,
        },
    });
    expect(".o_toy_view.o_view_controller").toHaveCount(1);
    expect(queryOne(".o_toy_view.toy").innerHTML).toBe(`<toy>Specific arch content</toy>`);
});

test("can click on action-bound links -- 1", async () => {
    expect.assertions(4);
    mockService("action", () => ({
        async doAction(actionRequest, options) {
            expect(actionRequest).toEqual({
                type: "ir.actions.client",
                tag: "someAction",
            });
            expect(options).toEqual({});
        },
    }));
    Animal._views[["toy", 1]] = /* xml */ `
        <toy>
            <a type="action" data-method="setTheControl" data-model="animal">link</a>
        </toy>
    `;
    onRpc("setTheControl", () => {
        expect.step("root called");
        return { type: "ir.actions.client", tag: "someAction" };
    });
    await mountWithCleanup(View, { props: { resModel: "animal", type: "toy", viewId: 1 } });
    expect("a").toHaveCount(1);
    click("a");
    await animationFrame();
    expect(["root called"]).toVerifySteps();
});

test("can click on action-bound links -- 2", async () => {
    expect.assertions(3);
    mockService("action", () => ({
        async doAction(actionRequest, options) {
            expect(actionRequest).toBe("myLittleAction");
            expect(options).toEqual({
                additionalContext: {
                    somekey: "somevalue",
                },
            });
        },
    }));
    Animal._views[["toy", 1]] = /* xml */ `
        <toy>
            <a type="action" name="myLittleAction" data-context="{ &quot;somekey&quot;: &quot;somevalue&quot; }">
                link
            </a>
        </toy>
    `;
    await mountWithCleanup(View, { props: { resModel: "animal", type: "toy", viewId: 1 } });
    expect("a").toHaveCount(1);
    click("a");
    await animationFrame();
});

test("can click on action-bound links -- 3", async () => {
    expect.assertions(3);
    mockService("action", () => ({
        async doAction(actionRequest, options) {
            expect(actionRequest).toEqual({
                domain: [["field", "=", "val"]],
                name: "myTitle",
                res_id: 66,
                res_model: "animal",
                target: "current",
                type: "ir.actions.act_window",
                views: [[55, "toy"]],
            });
            expect(options).toEqual({
                additionalContext: {
                    somekey: "somevalue",
                },
            });
        },
    }));
    Animal._views[["toy", 1]] = /* xml */ `
        <toy>
            <a type="action" title="myTitle" data-model="animal" data-resId="66" data-views="[[55, 'toy']]" data-domain="[['field', '=', 'val']]" data-context="{ &quot;somekey&quot;: &quot;somevalue&quot; }">
                link
            </a>
        </toy>
    `;
    await mountWithCleanup(View, { props: { resModel: "animal", type: "toy", viewId: 1 } });
    expect("a").toHaveCount(1);
    click("a");
    await animationFrame();
});

test("renders banner_route", async () => {
    expect.assertions(2);
    Animal._views[["toy", 1]] = /* xml */ `
        <toy banner_route="/mybody/isacage">
            <Banner t-if="env.config.bannerRoute" />
        </toy>
    `;
    onRpc("/mybody/isacage", () => {
        expect.step("root called");
        return { html: `<div class="setmybodyfree">myBanner</div>` };
    });
    await mountWithCleanup(View, { props: { resModel: "animal", type: "toy", viewId: 1 } });
    expect(".setmybodyfree").toHaveCount(1);
    expect(["root called"]).toVerifySteps();
});

test("renders banner_route with js and css assets", async () => {
    expect.assertions(2);
    Animal._views[["toy", 1]] = /* xml */ `
        <toy banner_route="/mybody/isacage">
            <Banner t-if="env.config.bannerRoute" />
        </toy>
    `;
    const bannerArch = `
        <div class="setmybodyfree">
            <link rel="stylesheet" href="/mystyle"/>
            <script type="text/javascript" src="/myscript"/>
            myBanner
        </div>
    `;
    onRpc("/mybody/isacage", () => {
        expect.step("root called");
        return { html: bannerArch };
    });
    const docCreateElement = document.createElement.bind(document);
    const createElement = (tagName) => {
        const elem = docCreateElement(tagName);
        if (tagName === "link") {
            Object.defineProperty(elem, "href", {
                set(href) {
                    if (href.includes("/mystyle")) {
                        expect.step("css loaded");
                    }
                    Promise.resolve().then(() => elem.dispatchEvent(new Event("load")));
                },
            });
        } else if (tagName === "script") {
            Object.defineProperty(elem, "src", {
                set(src) {
                    if (src.includes("/myscript")) {
                        expect.step("js loaded");
                    }
                    Promise.resolve().then(() => elem.dispatchEvent(new Event("load")));
                },
            });
        }
        return elem;
    };
    patchWithCleanup(document, { createElement });
    await mountWithCleanup(View, { props: { resModel: "animal", type: "toy", viewId: 1 } });
    expect(["root called", "js loaded", "css loaded"]).toVerifySteps();
    expect(".setmybodyfree").toHaveCount(1);
});

test("banner can re-render with new HTML", async () => {
    expect.assertions(6);
    Animal._views[["toy", 1]] = /* xml */ `
        <toy banner_route="/mybody/isacage">
            <Banner t-if="env.config.bannerRoute" />
        </toy>
    `;
    const banners = [
        `<div class="banner1">
            <a type="action" data-method="setTheControl" data-model="animal" data-reload-on-close="true">link</a>
        </div>`,
        `<div class="banner2">
            MyBanner
        /div>`,
    ];
    onRpc("/mybody/isacage", () => {
        expect.step("/mybody/isacage");
        return { html: banners.shift() };
    });
    onRpc("setTheControl", () => {
        return { type: "ir.actions.act_window_close" };
    });
    await mountWithCleanup(View, { props: { resModel: "animal", type: "toy", viewId: 1 } });
    expect(["/mybody/isacage"]).toVerifySteps();
    expect(".banner1").toHaveCount(1);
    expect(".banner2").toHaveCount(0);
    click("a");
    await animationFrame();
    expect(["/mybody/isacage"]).toVerifySteps();
    expect(".banner1").toHaveCount(0);
    expect(".banner2").toHaveCount(1);
});

test("banner does not reload on render", async () => {
    expect.assertions(3);
    Animal._views[["toy", 1]] = /* xml */ `
        <toy banner_route="/mybody/isacage">
            <Banner t-if="env.config.bannerRoute" />
        </toy>
    `;
    const bannerArch = `
        <div class="setmybodyfree">
            myBanner
        </div>`;
    let toy;
    patchWithCleanup(ToyController.prototype, {
        setup() {
            super.setup();
            toy = this;
        },
    });
    onRpc("/mybody/isacage", () => {
        expect.step("/mybody/isacage");
        return { html: bannerArch };
    });
    await mountWithCleanup(View, { props: { resModel: "animal", type: "toy", viewId: 1 } });
    expect(["/mybody/isacage"]).toVerifySteps();
    await toy.render();
    await animationFrame();
    expect([]).toVerifySteps();
    expect(".setmybodyfree").toHaveCount(1);
});

test("click on action-bound links in banner (concurrency)", async () => {
    expect.assertions(1);
    const prom = new Deferred();
    mockService("action", () => ({
        async doAction(actionRequest) {
            expect(actionRequest).toEqual({
                type: "ir.actions.client",
                tag: "gout",
            });
            return true;
        },
    }));
    Animal._views[["toy", 1]] = /* xml */ `
        <toy banner_route="/banner_route">
            <Banner t-if="env.config.bannerRoute" />
            <a type="action" data-method="setTheControl" data-model="animal">link</a>
        </toy>
    `;
    onRpc("/banner_route", () => {
        return {
            html: `<div><a type="action" data-method="heartOfTheSun" data-model="animal">link</a></div>`,
        };
    });
    onRpc("setTheControl", async () => {
        await prom;
        return {
            type: "ir.actions.client",
            tag: "toug",
        };
    });
    onRpc("heartOfTheSun", () => {
        return {
            type: "ir.actions.client",
            tag: "gout",
        };
    });
    await mountWithCleanup(View, { props: { resModel: "animal", type: "toy", viewId: 1 } });
    click("a[data-method='setTheControl']");
    await animationFrame();
    click("a[data-method='heartOfTheSun']");
    prom.resolve();
    await animationFrame();
});

test("real life banner", async () => {
    expect.assertions(6);
    mockService("action", () => ({
        async doAction() {},
    }));
    Animal._views[["toy", 1]] = /* xml */ `
        <toy banner_route="/mybody/isacage">
            <Banner t-if="env.config.bannerRoute" />
        </toy>
    `;
    const bannerArch = `
        <div class="modal o_onboarding_modal o_technical_modal" tabindex="-1" role="dialog">
            <div class="modal-dialog" role="document">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Remove Configuration Tips</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <p>Do you want to remove this configuration panel?</p>
                    </div>
                    <div class="modal-footer">
                        <a type="action" class="btn btn-primary" data-bs-dismiss="modal" data-model="mah.model" data-method="mah_method" data-o-hide-banner="true">Remove</a>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Discard</button>
                    </div>
                </div>
            </div>
        </div>
        <div class="o_onboarding" />
            <div class="o_onboarding_wrap" />
                <a href="#" data-bs-toggle="modal" data-bs-target=".o_onboarding_modal" class="float-end o_onboarding_btn_close">
                    <i class="fa fa-times" title="Close the onboarding panel" id="closeOnboarding"></i>
                </a>
                <div class="bannerContent">Content</div>
            </div>
        </div>`;
    onRpc("/mybody/isacage", async () => {
        expect.step("/mybody/isacage");
        return { html: bannerArch };
    });
    onRpc("/web/dataset/call_kw/mah.model/mah_method", async (request) => {
        expect.step(new URL(request.url).pathname);
        return true;
    });
    await mountWithCleanup(View, { props: { resModel: "animal", type: "toy", viewId: 1 } });
    expect(["/mybody/isacage"]).toVerifySteps();
    expect(".modal").not.toBeVisible();
    expect(".o_onboarding_container").toHaveClass("o-vertical-slide");
    click("#closeOnboarding");
    await animationFrame();
    expect(".modal").toBeVisible();
    click(queryOne(".modal a[type='action']"));
    await animationFrame();
    expect(["/web/dataset/call_kw/mah.model/mah_method"]).toVerifySteps();

    runAllTimers();
    await animationFrame();
    expect(".o_onboarding_container").toHaveCount(0);
});

////////////////////////////////////////////////////////////////////////////
// js_class
////////////////////////////////////////////////////////////////////////////

test("rendering with given jsClass", async function () {
    expect.assertions(4);
    onRpc("get_views", (_, { kwargs }) => {
        expect(kwargs.views).toEqual([[false, "toy"]]);
        expect(pick(kwargs.options, "action_id", "load_filters", "toolbar")).toEqual({
            action_id: false,
            load_filters: false,
            toolbar: false,
        });
    });

    await mountWithCleanup(View, { props: { resModel: "animal", type: "toy_imp" } });
    expect(".o_toy_view.toy_imp").toHaveCount(1);
    expect(".o_toy_view.toy_imp").toHaveText("Arch content (id=false)");
});

test("rendering with loaded arch attribute 'js_class'", async function () {
    expect.assertions(4);
    onRpc("get_views", (_, { kwargs }) => {
        expect(kwargs.views).toEqual([[2, "toy"]]);
        expect(pick(kwargs.options, "action_id", "load_filters", "toolbar")).toEqual({
            action_id: false,
            load_filters: false,
            toolbar: false,
        });
    });
    await mountWithCleanup(View, { props: { resModel: "animal", type: "toy", viewId: 2 } });
    expect(".o_toy_view.toy_imp").toHaveCount(1);
    expect(".o_toy_view.toy_imp").toHaveText("Arch content (id=2)");
});

test("rendering with given arch attribute 'js_class'", async function () {
    expect.assertions(2);
    onRpc("get_views", () => {
        throw new Error("no get_views expected");
    });
    await mountWithCleanup(View, {
        props: {
            resModel: "animal",
            type: "toy",
            arch: `<toy js_class="toy_imp">Specific arch content for specific class</toy>`,
            fields: {},
        },
    });
    expect(".o_toy_view.toy_imp").toHaveCount(1);
    expect(".o_toy_view.toy_imp").toHaveText("Specific arch content for specific class");
});

test("rendering with loaded arch attribute 'js_class' and given jsClass", async function () {
    expect.assertions(3);
    viewRegistry.add("toy_2", {
        type: "toy",
        Controller: class extends Component {
            static props = ["*"];
            static template = xml`<div class="o_toy_view_2"/>`;
            static type = "toy";
        },
    });
    onRpc("get_views", (_, { kwargs }) => {
        expect(kwargs.views).toEqual([[2, "toy"]]);
        expect(pick(kwargs.options, "action_id", "load_filters", "toolbar")).toEqual({
            action_id: false,
            load_filters: false,
            toolbar: false,
        });
    });
    await mountWithCleanup(View, {
        props: {
            resModel: "animal",
            type: "toy_2",
            viewId: 2,
        },
    });
    expect(".o_toy_view.toy_imp").toHaveCount(1);
});

test("rendering with given arch attribute 'js_class' and given jsClass", async function () {
    expect.assertions(1);
    viewRegistry.add(
        "toy_2",
        {
            type: "toy",
            Controller: class extends Component {
                static props = ["*"];
                static template = xml`<div class="o_toy_view_2"/>`;
                static type = "toy";
            },
        },
        { force: true }
    );
    onRpc("get_views", () => {
        throw new Error("no get_views expected");
    });
    await mountWithCleanup(View, {
        props: {
            resModel: "animal",
            type: "toy_2",
            arch: `<toy js_class="toy_imp"/>`,
            fields: {},
        },
    });
    expect(".o_toy_view.toy_imp").toHaveCount(1);
});

////////////////////////////////////////////////////////////////////////////
// props validation
////////////////////////////////////////////////////////////////////////////

test("'resModel' must be passed as prop", async function () {
    const props = {};
    try {
        await mountWithCleanup(View, { props });
    } catch (error) {
        expect.step(error.message);
    }
    expect([`View props should have a "resModel" key`]).toVerifySteps();
});

test("'type' must be passed as prop", async function () {
    const props = { resModel: "animal" };
    try {
        await mountWithCleanup(View, { props });
    } catch (error) {
        expect.step(error.message);
    }
    expect([`View props should have a "type" key`]).toVerifySteps();
});

test("'arch' cannot be passed as prop alone", async function () {
    const props = { resModel: "animal", type: "toy", arch: "<toy/>" };
    try {
        await mountWithCleanup(View, { props });
    } catch (error) {
        expect.step(error.message);
    }
    expect([`"arch" and "fields" props must be given together`]).toVerifySteps();
});

test("'fields' cannot be passed as prop alone", async function () {
    const props = { resModel: "animal", type: "toy", fields: {} };
    try {
        await mountWithCleanup(View, { props });
    } catch (error) {
        expect.step(error.message);
    }
    expect([`"arch" and "fields" props must be given together`]).toVerifySteps();
});

test("'searchViewArch' cannot be passed as prop alone", async function () {
    const props = { resModel: "animal", type: "toy", searchViewArch: "<toy/>" };
    try {
        await mountWithCleanup(View, { props });
    } catch (error) {
        expect.step(error.message);
    }
    expect([
        `"searchViewArch" and "searchViewFields" props must be given together`,
    ]).toVerifySteps();
});

test("'searchViewFields' cannot be passed as prop alone", async function () {
    const props = { resModel: "animal", type: "toy", searchViewFields: {} };
    try {
        await mountWithCleanup(View, { props });
    } catch (error) {
        expect.step(error.message);
    }
    expect([
        `"searchViewArch" and "searchViewFields" props must be given together`,
    ]).toVerifySteps();
});

////////////////////////////////////////////////////////////////////////////
// props
////////////////////////////////////////////////////////////////////////////

test("search query props are passed as props to concrete view (default search arch)", async function () {
    expect.assertions(4);
    class ToyController extends Component {
        static props = ["*"];
        static template = xml`<div/>`;
        setup() {
            const { context, domain, groupBy, orderBy } = this.props;
            expect(context).toEqual({
                lang: "en",
                tz: "taht",
                uid: 7,
                key: "val",
                allowed_company_ids: [1],
            });
            expect(domain).toEqual([[0, "=", 1]]);
            expect(groupBy).toEqual(["birthday"]);
            expect(orderBy).toEqual([{ name: "bar", asc: true }]);
        }
    }
    viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });
    const props = {
        resModel: "animal",
        type: "toy",
        domain: [[0, "=", 1]],
        groupBy: ["birthday"],
        context: { key: "val" },
        orderBy: [{ name: "bar", asc: true }],
    };
    await mountWithCleanup(View, { props });
});

test("non empty prop 'noContentHelp'", async function () {
    expect.assertions(1);
    class ToyController extends Component {
        static props = ["*"];
        static template = xml`<div/>`;
        setup() {
            expect(this.props.info.noContentHelp).toBe("<div>Help</div>");
        }
    }
    viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });
    const props = {
        resModel: "animal",
        type: "toy",
        noContentHelp: "<div>Help</div>",
    };
    await mountWithCleanup(View, { props });
});

test("useSampleModel false by default", async function () {
    expect.assertions(1);
    class ToyController extends Component {
        static props = ["*"];
        static template = xml`<div/>`;
        setup() {
            expect(this.props.useSampleModel).toBe(false);
        }
    }
    viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });
    const props = { resModel: "animal", type: "toy" };
    await mountWithCleanup(View, { props });
});

test("sample='1' on arch", async function () {
    expect.assertions(1);
    class ToyController extends Component {
        static props = ["*"];
        static template = xml`<div/>`;
        setup() {
            expect(this.props.useSampleModel).toBe(true);
        }
    }
    viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });
    const props = {
        resModel: "animal",
        type: "toy",
        arch: `<toy sample="1"/>`,
        fields: {},
    };
    await mountWithCleanup(View, { props });
});

test("sample='0' on arch and useSampleModel=true", async function () {
    expect.assertions(1);
    class ToyController extends Component {
        static props = ["*"];
        static template = xml`<div/>`;
        setup() {
            expect(this.props.useSampleModel).toBe(true);
        }
    }
    viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });
    const props = {
        resModel: "animal",
        type: "toy",
        useSampleModel: true,
        arch: `<toy sample="0"/>`,
        fields: {},
    };
    await mountWithCleanup(View, { props });
});

test("sample='1' on arch and useSampleModel=false", async function () {
    expect.assertions(1);
    class ToyController extends Component {
        static props = ["*"];
        static template = xml`<div/>`;
        setup() {
            expect(this.props.useSampleModel).toBe(false);
        }
    }
    viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });
    const props = {
        resModel: "animal",
        type: "toy",
        useSampleModel: false,
        arch: `<toy sample="1"/>`,
        fields: {},
    };
    await mountWithCleanup(View, { props });
});

test("useSampleModel=true", async function () {
    expect.assertions(1);
    class ToyController extends Component {
        static props = ["*"];
        static template = xml`<div/>`;
        setup() {
            expect(this.props.useSampleModel).toBe(true);
        }
    }
    viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });
    const props = { resModel: "animal", type: "toy", useSampleModel: true };
    await mountWithCleanup(View, { props });
});

test("rendering with given prop", async function () {
    expect.assertions(1);
    class ToyController extends Component {
        static props = ["*"];
        static template = xml`<div/>`;
        setup() {
            expect(this.props.specificProp).toBe("specificProp");
        }
    }
    viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });
    const props = { resModel: "animal", type: "toy", specificProp: "specificProp" };
    await mountWithCleanup(View, { props });
});

test("search query props are passed as props to concrete view (specific search arch)", async function () {
    expect.assertions(4);
    class ToyController extends Component {
        static props = ["*"];
        static template = xml`<div/>`;
        setup() {
            const { context, domain, groupBy, orderBy } = this.props;
            expect(context).toEqual({
                lang: "en",
                tz: "taht",
                uid: 7,
                allowed_company_ids: [1],
            });
            expect(domain).toEqual(["&", [0, "=", 1], [1, "=", 1]]);
            expect(groupBy).toEqual(["display_name"]);
            expect(orderBy).toEqual([{ name: "bar", asc: true }]);
        }
    }
    viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });
    const props = {
        type: "toy",
        resModel: "animal",
        searchViewId: 1,
        domain: [[0, "=", 1]],
        groupBy: ["birthday"],
        context: { search_default_filter: 1, search_default_group_by: 1 },
        orderBy: [{ name: "bar", asc: true }],
    };
    await mountWithCleanup(View, { props });
});

test("multiple ways to pass classes for styling", async () => {
    const props = {
        resModel: "animal",
        type: "toy",
        className: "o_custom_class_from_props_1 o_custom_class_from_props_2",
        arch: `
            <toy
                js_class="toy_imp"
                class="o_custom_class_from_arch_1 o_custom_class_from_arch_2"
            />
        `,
        fields: {},
    };
    await mountWithCleanup(View, { props });
    const view = queryOne(".o_toy_view");
    expect(view).toHaveClass("o_toy_imp_view", {
        message: "should have the class from js_class attribute",
    });
    expect(view).toHaveClass("o_custom_class_from_props_1", {
        message: "should have the class from props",
    });
    expect(view).toHaveClass("o_custom_class_from_props_2", {
        message: "should have the class from props",
    });
    expect(view).toHaveClass("o_custom_class_from_arch_1", {
        message: "should have the class from arch",
    });
    expect(view).toHaveClass("o_custom_class_from_arch_2", {
        message: "should have the class from arch",
    });
});

test("callback recorders are moved from props to subenv", async () => {
    expect.assertions(5);
    class ToyController extends Component {
        static props = ["*"];
        static template = xml`<div/>`;
        setup() {
            expect(this.env.__getGlobalState__).toBeInstanceOf(CallbackRecorder); // put in env by View
            expect(this.env.__getContext__).toBeInstanceOf(CallbackRecorder); // put in env by View
            expect(this.env.__getLocalState__).toBe(null); // set by View
            expect(this.env.__beforeLeave__).toBe(null); // set by View
            expect(this.env.__getOrderBy__).toBeInstanceOf(CallbackRecorder); // put in env by WithSearch
        }
    }
    viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });
    const props = {
        type: "toy",
        resModel: "animal",
        __getGlobalState__: new CallbackRecorder(),
        __getContext__: new CallbackRecorder(),
    };
    await mountWithCleanup(View, { props });
});

////////////////////////////////////////////////////////////////////////////
// update props
////////////////////////////////////////////////////////////////////////////

test("react to prop 'domain' changes", async function () {
    expect.assertions(2);
    class ToyController extends Component {
        static props = ["*"];
        static template = xml`<div/>`;
        setup() {
            onWillStart(() => {
                expect(this.props.domain).toEqual([["type", "=", "carnivorous"]]);
            });
            onWillUpdateProps((nextProps) => {
                expect(nextProps.domain).toEqual([["type", "=", "herbivorous"]]);
            });
        }
    }
    viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });
    class Parent extends Component {
        static props = ["*"];
        static template = xml`<View t-props="state"/>`;
        static components = { View };
        setup() {
            this.state = useState({
                type: "toy",
                resModel: "animal",
                domain: [["type", "=", "carnivorous"]],
            });
        }
    }
    const parent = await mountWithCleanup(Parent);
    parent.state.domain = [["type", "=", "herbivorous"]];
    await animationFrame();
});
