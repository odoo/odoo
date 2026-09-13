// @ts-check
import { afterEach, beforeEach, expect, test } from "@odoo/hoot";
import { queryAllTexts, queryText, queryValue } from "@odoo/hoot-dom";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { Component, EventBus, onError, reactive, useState, xml } from "@odoo/owl";
import {
    contains,
    defineModels,
    fields,
    getService,
    makeMockEnv,
    models,
    mountView,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { enableLogging, getStatus, makeLogger } from "@web/core/debug/debug_logger";
import { StatusBarField } from "@web/fields/display/statusbar/statusbar_field";
import { Many2ManyCheckboxesField } from "@web/fields/relational/many2many_checkboxes/many2many_checkboxes_field";
import { ReferenceField } from "@web/fields/relational/reference/reference_field";
import { useSpecialData } from "@web/fields/relational/special_data";
import { BadgeSelectionField } from "@web/fields/selection/badge_selection/badge_selection_field";
import { RadioField } from "@web/fields/selection/radio/radio_field";
import { DomainField } from "@web/fields/specialized/domain/domain_field";
import { FormController } from "@web/views/form/form_controller";

let controller;
const log = makeLogger("web.field.regression");
let previousLogSpec;
beforeEach(() => {
    previousLogSpec = getStatus().spec;
    enableLogging("web.field.*", { persist: false });
    log.logic("browser dimensions", {
        width: window.innerWidth,
        height: window.innerHeight,
    });
    patchWithCleanup(FormController.prototype, {
        setup() {
            super.setup();
            controller = this;
        },
    });
});
afterEach(() => enableLogging(previousLogSpec, { persist: false }));

class AuditOption extends models.Model {
    _name = "audit.option";
    name = fields.Char();
    _records = [
        { id: 1, name: "First" },
        { id: 2, name: "Second" },
        { id: 3, name: "Third" },
    ];
}
class AuditRecord extends models.Model {
    _name = "audit.record";
    name = fields.Char();
    domain_value = fields.Char();
    model_name = fields.Char();
    reference = fields.Char();
    tags = fields.Many2many({ relation: "audit.option" });
    progress = fields.Integer();
    capacity = fields.Integer();
    filter_id = fields.Integer({ default: 1 });
    choice = fields.Many2one({ relation: "audit.option" });
    _records = [
        {
            id: 1,
            name: "Record",
            domain_value: "[]",
            model_name: "audit.option",
            reference: "audit.option,1",
            tags: [],
            progress: 5,
            capacity: 0,
        },
    ];
}
defineModels([AuditRecord, AuditOption]);

test("domain: invalid newer input versus old successful count", async () => {
    const pending = new Deferred();
    /** @type {DomainField} */
    let widget;
    patchWithCleanup(DomainField.prototype, {
        setup() {
            super.setup();
            widget = this;
        },
    });
    onRpc("audit.option", "search_count", () => {
        log.pipeline("domain count started");
        return pending;
    });
    await mountView({
        type: "form",
        resModel: "audit.record",
        resId: 1,
        arch: `<form><field name="domain_value" widget="domain" options="{'model': 'audit.option', 'in_dialog': True}"/></form>`,
    });
    await controller.model.root.update({
        domain_value: `[("id", "=", context.get('id'))]`,
    });
    await animationFrame();
    log.logic("domain before old response", {
        state: { ...widget.state },
        panel: queryText(".o_field_domain_panel"),
    });
    expect(widget.state.isValid).toBe(false);
    expect(".o_domain_show_selection_button").toHaveCount(0);
    pending.resolve(42);
    await animationFrame();
    log.logic("domain after old response", {
        state: { ...widget.state },
        panel: queryText(".o_field_domain_panel"),
    });
    expect(widget.state.isValid).toBe(false);
    expect(".o_domain_show_selection_button").toHaveCount(0);
});

test("domain: cleared model cancels pending count", async () => {
    const pending = new Deferred();
    /** @type {DomainField} */
    let widget;
    patchWithCleanup(DomainField.prototype, {
        setup() {
            super.setup();
            widget = this;
        },
    });
    onRpc("audit.option", "search_count", () => pending);
    await mountView({
        type: "form",
        resModel: "audit.record",
        resId: 1,
        arch: `<form><field name="model_name"/><field name="domain_value" widget="domain" options="{'model': 'model_name', 'in_dialog': True}"/></form>`,
    });
    await controller.model.root.update({ model_name: false });
    await animationFrame();
    pending.resolve(42);
    await animationFrame();
    log.logic("cleared model actual DOM", {
        state: { ...widget.state },
        text: queryText(".o_field_widget[name=domain_value]"),
    });
    expect(widget.state.recordCount).toBe(null);
    expect(".o_domain_show_selection_button").toHaveCount(0);
    expect(".o_field_widget[name=domain_value]").toHaveText(
        "Select a model to add a filter.",
    );
});

test("reference: name response before next observer frame", async () => {
    const pending = new Deferred();
    /** @type {ReferenceField} */
    let widget;
    const requested = [];
    patchWithCleanup(ReferenceField.prototype, {
        setup() {
            super.setup();
            widget = this;
        },
    });
    onRpc("audit.option", "web_search_read", ({ kwargs }) => {
        const ids = kwargs.domain[0][2];
        requested.push(...ids);
        log.pipeline("reference names", { ids });
        if (ids.includes(2)) {
            return pending;
        }
    });
    await mountView({
        type: "form",
        resModel: "audit.record",
        resId: 1,
        arch: `<form><field name="reference" widget="reference"/></form>`,
    });
    await controller.model.root.update({ reference: "audit.option,2" });
    await animationFrame();
    expect(requested.includes(2)).toBe(true);
    await controller.model.root.update({ reference: "audit.option,3" });
    pending.resolve({ length: 1, records: [{ id: 2, display_name: "Second" }] });
    // Drain service/update promise continuations without running the next RAF.
    for (let i = 0; i < 15; i++) {
        await Promise.resolve();
    }
    await animationFrame();
    await animationFrame();
    log.logic("reference settled", {
        stored: controller.model.root.data.reference,
        formatted: widget.state.formattedCharValue,
        shown: queryValue(".o_field_widget[name=reference] input"),
        requested,
    });
    expect(controller.model.root.data.reference).toBe("audit.option,3");
    expect(widget.state.formattedCharValue).toEqual({
        resId: 3,
        resModel: "audit.option",
        displayName: "Third",
    });
    expect(".o_field_widget[name=reference] input").toHaveValue("Third");
    expect(requested.includes(3)).toBe(true);
});

for (const [count, excluded] of /** @type {[number, boolean][]} */ ([
    [149, false],
    [250, false],
    [149, true],
])) {
    test(`checkboxes: ${count} selected rows, excluded=${excluded}`, async () => {
        AuditOption._records = Array.from({ length: count }, (_, i) => ({
            id: i + 1,
            name: `Option ${i + 1}`,
        }));
        AuditRecord._records[0].tags = AuditOption._records.map((r) => r.id);
        const requests = [];
        onRpc("audit.option", "name_search", ({ args, kwargs }) => {
            requests.push({ args, kwargs });
            log.pipeline("checkbox name_search boundary", { args, kwargs });
        });
        await mountView({
            type: "form",
            resModel: "audit.record",
            resId: 1,
            arch: `<form><field name="tags" widget="many2many_checkboxes" domain="${excluded ? "[('id', '=', -1)]" : "[]"}"/></form>`,
        });
        expect(".o_field_widget[name=tags] input:checked").toHaveCount(count);
        expect(controller.model.root.data.tags.currentIds).toHaveLength(count);
        log.logic("checkbox actual DOM", {
            selected: count,
            excluded,
            requests: requests.length,
        });
    });
}

test("special data: real Owl scheduling with old response after newer props", async () => {
    const pending = new Map();
    /** @type {Parent} */
    let parent;
    class Child extends Component {
        static props = ["record", "requestKey"];
        static template = xml`<span class="special-result" t-esc="result.data"/>`;
        setup() {
            this.result = useSpecialData((orm, props) => {
                const key = props.requestKey;
                log.pipeline("special data load", { key });
                if (key === "initial") {
                    return Promise.resolve(key);
                }
                const def = new Deferred();
                pending.set(key, def);
                return def;
            });
        }
    }
    class Parent extends Component {
        static props = [];
        static components = { Child };
        static template = xml`<Child record="record" requestKey="state.key"/>`;
        setup() {
            this.record = reactive({
                model: { specialDataCaches: new Map(), bus: new EventBus() },
            });
            this.state = useState({ key: "initial" });
            parent = this;
        }
    }
    await mountWithCleanup(Parent);
    parent.state.key = "A";
    await animationFrame();
    parent.state.key = "B";
    await animationFrame();
    expect([...pending.keys()]).toEqual(["A", "B"]);
    pending.get("A").resolve("A");
    await animationFrame();
    log.logic("special data rendered old response", {
        current: parent.state.key,
        shown: queryText(".special-result"),
    });
    expect(".special-result").toHaveText("initial");
    pending.get("B").resolve("B");
    await animationFrame();
    expect(".special-result").toHaveText("B");
});

test("progress: configured zero maximum is preserved", async () => {
    await mountView({
        type: "form",
        resModel: "audit.record",
        resId: 1,
        arch: `<form><field name="progress" widget="progressbar" options="{'max_value': 'capacity'}"/><field name="capacity"/></form>`,
    });
    log.logic("progress maximum", {
        stored: controller.model.root.data.capacity,
        text: queryText(".o_progressbar_value"),
    });
    expect(controller.model.root.data.capacity).toBe(0);
    expect(".o_progress").toHaveAttribute("aria-valuemax", "0");
    expect(queryText(".o_progressbar_value").replace(/\s+/g, " ")).toBe("5 / 0");
    await controller.model.root.update({ capacity: 10 });
    await animationFrame();
    expect(queryText(".o_progressbar_value").replace(/\s+/g, " ")).toBe("5 / 10");
    await controller.model.root.update({ capacity: 0 });
    await animationFrame();
    expect(queryText(".o_progressbar_value").replace(/\s+/g, " ")).toBe("5 / 0");
});

test("special data: selection waits for choices matching the current domain", async () => {
    const pendingA = new Deferred();
    const pendingB = new Deferred();
    const seen = [];
    onRpc("audit.option", "name_search", ({ args }) => {
        const id = args[1][0][2];
        seen.push(id);
        log.pipeline("selection request", { id });
        if (id === 2) {
            return pendingA;
        }
        if (id === 3) {
            return pendingB;
        }
    });
    await mountView({
        type: "form",
        resModel: "audit.record",
        resId: 1,
        arch: `<form><field name="filter_id"/><field name="choice" widget="selection" domain="[('id', '=', filter_id)]"/></form>`,
    });
    await controller.model.root.update({ filter_id: 2 });
    await animationFrame();
    await controller.model.root.update({ filter_id: 3 });
    await animationFrame();
    expect(seen.includes(2) && seen.includes(3)).toBe(true);
    expect(".o_field_widget[name=choice] input").toHaveAttribute("disabled");
    pendingA.resolve([[2, "Second"]]);
    await animationFrame();
    expect(".o_field_widget[name=choice] input").toHaveAttribute("disabled");
    expect(controller.model.root.data.choice).toBe(false);
    pendingB.resolve([[3, "Third"]]);
    await animationFrame();
    await contains(".o_field_widget[name=choice] input").click();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Third"]);
});

test("domain: later RPC wins when both inputs start requests", async () => {
    const requests = [];
    onRpc("audit.option", "search_count", () => {
        const request = new Deferred();
        requests.push(request);
        return request;
    });
    await mountView({
        type: "form",
        resModel: "audit.record",
        resId: 1,
        arch: `<form><field name="domain_value" widget="domain" options="{'model': 'audit.option', 'in_dialog': True}"/></form>`,
    });
    await controller.model.root.update({ domain_value: "[('id', '=', 1)]" });
    await animationFrame();
    expect(requests).toHaveLength(2);
    requests[1].resolve(1);
    requests[0].resolve(42);
    await animationFrame();
    expect(".o_domain_show_selection_button").toHaveText("1 record(s)");
    log.logic("domain ordinary request ordering control", {
        panel: queryText(".o_field_domain_panel"),
    });
});

test("special data: shared cache refresh reaches current subscribers only", async () => {
    await makeMockEnv();
    const callbacks = new Map();
    const loads = [];
    patchWithCleanup(getService("orm"), {
        cache({ callback }) {
            return /** @type {import("@web/core/network/orm_service").ORM} */ ({
                call(model, method, args) {
                    callbacks.set(args[0], callback);
                    log.pipeline("cache miss", { key: args[0] });
                    return Promise.resolve(args[0]);
                },
            });
        },
    });
    /** @type {Parent} */
    let parent;
    class Child extends Component {
        static props = ["record", "requestKey", "id"];
        static template = xml`<span t-att-class="props.id" t-esc="result.data"/>`;
        setup() {
            this.result = useSpecialData((orm, props) => {
                loads.push(`${props.id}:${props.requestKey}`);
                return orm.call("audit.option", "special", [props.requestKey]);
            });
        }
    }
    class Parent extends Component {
        static props = [];
        static components = { Child };
        static template = xml`<t t-if="state.visible"><Child record="record" requestKey="state.key" id="'first'"/><Child record="record" requestKey="'A'" id="'second'"/></t>`;
        setup() {
            this.record = reactive({ model: { specialDataCaches: new Map() } });
            this.state = useState({ key: "A", visible: true });
            parent = this;
        }
    }
    await mountWithCleanup(Parent);
    expect(callbacks.size).toBe(1);
    callbacks.get("A")("refreshed", true);
    await animationFrame();
    expect(".first").toHaveText("refreshed");
    expect(".second").toHaveText("refreshed");
    parent.state.key = "B";
    await animationFrame();
    const firstLoads = loads.filter((key) => key.startsWith("first:")).length;
    callbacks.get("A")("refreshed again", true);
    await animationFrame();
    expect(".first").toHaveText("B");
    expect(".second").toHaveText("refreshed again");
    expect(loads.filter((key) => key.startsWith("first:"))).toHaveLength(firstLoads);
    parent.state.visible = false;
    await animationFrame();
    const count = loads.length;
    callbacks.get("A")("after destruction", true);
    callbacks.get("B")("after destruction", true);
    await animationFrame();
    expect(loads).toHaveLength(count);
});

test("domain: clearing the model also cancels pending facet descriptions", async () => {
    /** @type {DomainField} */
    let widget;
    patchWithCleanup(DomainField.prototype, {
        setup() {
            super.setup();
            widget = this;
        },
    });
    await mountView({
        type: "form",
        resModel: "audit.record",
        resId: 1,
        arch: `<form><field name="model_name"/><field name="domain_value" widget="domain" options="{'model': 'model_name', 'in_dialog': True}"/></form>`,
    });
    const pending = new Deferred();
    patchWithCleanup(widget.treeProcessor, {
        treeFromDomain: () => pending,
        getDomainTreeDescription: () => "old facet",
    });
    const loading = widget.loadFacets();
    await controller.model.root.update({ model_name: false });
    await widget.loadFacets();
    pending.resolve({ value: "leaf" });
    await loading;
    log.logic("facet request settled after clearing model", {
        facets: widget.state.facets,
    });
    expect(widget.state.facets).toEqual([]);
    expect(widget.state.folded).toBe(false);
});

for (const { name, ComponentClass, field, selector, invoke } of [
    {
        name: "radio",
        ComponentClass: RadioField,
        field: "choice",
        selector: "input",
        invoke: (widget) => widget.onChange([1, "First"]),
    },
    {
        name: "selection_badge",
        ComponentClass: BadgeSelectionField,
        field: "choice",
        selector: ".o_selection_badge",
        invoke: (widget) => widget.onChange(1),
    },
    {
        name: "many2many_checkboxes",
        ComponentClass: Many2ManyCheckboxesField,
        field: "tags",
        selector: "input",
        invoke: (widget) => widget.onChange(1, true),
    },
    {
        name: "statusbar",
        ComponentClass: StatusBarField,
        field: "choice",
        selector: "button:not(.d-none)",
        invoke: (widget) => widget.selectItem({ value: 1, label: "First" }),
    },
]) {
    test(`${name}: an event from old choices cannot write while loading`, async () => {
        /** @type {RadioField | BadgeSelectionField | Many2ManyCheckboxesField | StatusBarField} */
        let widget;
        patchWithCleanup(ComponentClass.prototype, {
            setup() {
                super.setup();
                widget = this;
            },
        });
        const pending = new Deferred();
        onRpc(
            "audit.option",
            name === "statusbar" ? "search_read" : "name_search",
            ({ args, kwargs }) => {
                const domain = name === "statusbar" ? kwargs.domain : args[1];
                log.pipeline("replacement choices requested", { name, domain });
                if (domain[0][2] === 2) {
                    return pending;
                }
            },
        );
        await mountView({
            type: "form",
            resModel: "audit.record",
            resId: 1,
            arch: `<form><field name="filter_id"/><field name="${field}" widget="${name}" domain="[('id', '=', filter_id)]" options="{'clickable': True}"/></form>`,
        });
        await controller.model.root.update({ filter_id: 2 });
        await animationFrame();
        expect(widget.specialData.isReady).toBe(false);
        const target = `.o_field_widget[name=${field}] ${selector}`;
        if (name === "selection_badge") {
            expect(target).toHaveAttribute("aria-disabled", "true");
        } else {
            expect(`${target}:not([disabled])`).toHaveCount(0);
        }
        await invoke(widget);
        expect(
            field === "tags"
                ? controller.model.root.data.tags.currentIds
                : controller.model.root.data[field],
        ).toEqual(field === "tags" ? [] : false);
        pending.resolve(
            name === "statusbar"
                ? [{ id: 2, display_name: "Second" }]
                : [[2, "Second"]],
        );
        await animationFrame();
        expect(widget.specialData.isReady).toBe(true);
    });
}

// Keep this file in the mobile lane's discovery set as well as the desktop lane.
test.tags("mobile");
test("replacement selection choices work with touch input", async () => {
    await mountView({
        type: "form",
        resModel: "audit.record",
        resId: 1,
        arch: `<form><field name="choice" widget="selection"/></form>`,
    });
    await contains(".o_field_widget[name=choice] input").click();
    await contains(".o_select_menu_item:contains(Third)").click();
    expect(controller.model.root.data.choice.id).toBe(3);
});

test("special data: replacement during initial loading never renders uninitialized data", async () => {
    await makeMockEnv();
    const requests = new Map();
    /** @type {Parent} */
    let parent;
    class Child extends Component {
        static props = ["record"];
        static template = xml`<span class="initial-result" t-esc="result.data.join(',')"/>`;
        setup() {
            this.result = useSpecialData((orm, props) => {
                const key = props.record.data.key;
                const pending = new Deferred();
                requests.set(key, pending);
                log.pipeline("initial load", { key });
                return pending;
            });
        }
    }
    class Parent extends Component {
        static props = [];
        static components = { Child };
        static template = xml`<Child record="record"/>`;
        setup() {
            parent = this;
            this.record = reactive({
                data: { key: 1 },
                model: { specialDataCaches: new Map() },
            });
        }
    }
    const mounted = mountWithCleanup(Parent);
    await animationFrame();
    expect(requests.has(1)).toBe(true);
    parent.record.data.key = 2;
    await animationFrame();
    expect(requests.has(2)).toBe(true);
    requests.get(1).resolve(["old"]);
    await animationFrame();
    expect(".initial-result").toHaveCount(0);
    requests.get(2).resolve(["current"]);
    await mounted;
    expect(".initial-result").toHaveText("current");
});

test("special data: current initial data mounts without waiting for an obsolete request", async () => {
    await makeMockEnv();
    const old = new Deferred();
    const requests = [];
    const record = reactive({
        data: { key: 1 },
        model: { specialDataCaches: new Map() },
    });
    class Child extends Component {
        static props = ["record"];
        static template = xml`<span class="latest-initial" t-esc="result.data"/>`;
        setup() {
            this.result = useSpecialData((orm, props) => {
                requests.push(props.record.data.key);
                return props.record.data.key === 1 ? old : Promise.resolve("current");
            });
        }
    }
    const mounted = mountWithCleanup(Child, { props: { record } });
    await animationFrame();
    expect(requests).toEqual([1]);
    record.data.key = 2;
    await animationFrame();
    expect(requests).toEqual([1, 2]);
    log.logic("mount while obsolete request remains pending", {
        shown: queryAllTexts(".latest-initial"),
    });
    expect(".latest-initial").toHaveText("current");
    old.resolve("obsolete");
    await mounted;
    expect(".latest-initial").toHaveText("current");
});

test("special data: an obsolete rejection does not report an error after newer data", async () => {
    const old = new Deferred();
    const record = reactive({
        data: { key: 0 },
        model: { specialDataCaches: new Map() },
    });
    class Child extends Component {
        static props = ["record"];
        static template = xml`<span class="latest-success" t-esc="result.data"/>`;
        setup() {
            this.result = useSpecialData((orm, props) =>
                props.record.data.key === 1
                    ? old
                    : Promise.resolve(props.record.data.key),
            );
        }
    }
    await mountWithCleanup(Child, { props: { record } });
    record.data.key = 1;
    await animationFrame();
    record.data.key = 2;
    await animationFrame();
    old.reject(new Error("obsolete lookup failed"));
    await animationFrame();
    log.logic("current data after obsolete rejection", {
        shown: queryText(".latest-success"),
    });
    expect(".latest-success").toHaveText("2");
});

test("special data: switching records stops observing the previous record", async () => {
    const makeRecord = (key) =>
        reactive({ data: { key }, model: { specialDataCaches: new Map() } });
    const first = makeRecord(1);
    const second = makeRecord(2);
    const loads = [];
    class Child extends Component {
        static props = ["record"];
        static template = xml`<span class="current-record" t-esc="result.data"/>`;
        setup() {
            this.result = useSpecialData((orm, props) => {
                loads.push(props.record.data.key);
                return Promise.resolve(props.record.data.key);
            });
        }
    }
    class Parent extends Component {
        static props = [];
        static components = { Child };
        static template = xml`<Child record="state.record"/>`;
        setup() {
            this.state = useState({ record: first });
        }
    }
    const parent = await mountWithCleanup(Parent);
    if (!parent) {
        throw new Error("The record-switching probe did not mount");
    }
    parent.state.record = second;
    await animationFrame();
    const before = loads.length;
    first.data.key = 3;
    await animationFrame();
    log.logic("loads after changing retired record", { loads });
    expect(loads).toHaveLength(before);
    expect(".current-record").toHaveText("2");
});

test("special data: a current request failure remains visible and a later input recovers", async () => {
    expect.errors(1);
    const record = reactive({
        data: { key: 0 },
        model: { specialDataCaches: new Map() },
    });
    class Child extends Component {
        static props = ["record"];
        static template = xml`<span class="recoverable-result" t-esc="result.data"/>`;
        setup() {
            this.result = useSpecialData(async (orm, props) => {
                if (props.record.data.key === 1) {
                    throw new Error("current lookup failed");
                }
                return props.record.data.key;
            });
        }
    }
    const child = await mountWithCleanup(Child, { props: { record } });
    if (!child) {
        throw new Error("The special-data recovery probe did not mount");
    }
    record.data.key = 1;
    await animationFrame();
    expect.verifyErrors(["current lookup failed"]);
    expect(child.result.isReady).toBe(false);
    expect(".recoverable-result").toHaveText("0");
    record.data.key = 2;
    await animationFrame();
    log.logic("recovered from current failure", { ready: child.result.isReady });
    expect(child.result.isReady).toBe(true);
    expect(".recoverable-result").toHaveText("2");
});

test("special data: a replacement initial failure reaches the Owl error boundary once", async () => {
    await makeMockEnv();
    const old = new Deferred();
    const current = new Deferred();
    const record = reactive({
        data: { key: 0 },
        model: { specialDataCaches: new Map() },
    });
    const errors = [];
    const requests = [];
    class Child extends Component {
        static props = ["record"];
        static template = xml`<span t-esc="result.data"/>`;
        setup() {
            this.result = useSpecialData((orm, props) => {
                requests.push(props.record.data.key);
                return props.record.data.key ? current : old;
            });
        }
    }
    class Parent extends Component {
        static props = [];
        static components = { Child };
        static template = xml`<Child t-if="state.visible" record="record"/><span t-else="" class="load-error">Failed to load</span>`;
        setup() {
            this.record = record;
            this.state = useState({ visible: true });
            onError((error) => {
                errors.push(error);
                log.logic("initial load error boundary", { error });
                this.state.visible = false;
            });
        }
    }
    const mounted = mountWithCleanup(Parent);
    await animationFrame();
    expect(requests).toEqual([0]);
    record.data.key = 1;
    await animationFrame();
    expect(requests).toEqual([0, 1]);
    current.reject(new Error("replacement initial lookup failed"));
    await animationFrame();
    old.resolve("obsolete");
    await mounted;
    expect(errors).toHaveLength(1);
    expect(".load-error").toHaveText("Failed to load");
});
