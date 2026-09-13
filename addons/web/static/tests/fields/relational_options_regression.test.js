// @ts-check
import { afterEach, beforeEach, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { enableLogging, getStatus, makeLogger } from "@web/core/debug/debug_logger";
import { StatusBarField } from "@web/fields/display/statusbar/statusbar_field";
import { ReferenceField } from "@web/fields/relational/reference/reference_field";
import { FormController } from "@web/views/form/form_controller";

const log = makeLogger("web.field.relational_options");
let previousLogSpec;
/** @type {FormController} */
let controller;
beforeEach(() => {
    previousLogSpec = getStatus().spec;
    enableLogging("web.field.*", { persist: false });
    patchWithCleanup(FormController.prototype, {
        setup() {
            super.setup();
            controller = this;
        },
    });
});
afterEach(() => enableLogging(previousLogSpec, { persist: false }));

class Option extends models.Model {
    name = fields.Char();
    _records = Array.from({ length: 150 }, (_, i) => ({
        id: i + 1,
        name: `Option ${String(i + 1).padStart(3, "0")}`,
    }));
}
class Holder extends models.Model {
    name = fields.Char();
    choice = fields.Many2one({ relation: "option" });
    model_id = fields.Many2one({ relation: "ir.model" });
    reference = fields.Reference({
        selection: [
            ["option", "Option"],
            ["holder", "Holder"],
            ["ir.model", "Model"],
        ],
    });
    /** @type {{id: number, name: string, choice: number|false, model_id: number, reference: string|false}[]} */
    _records = [{ id: 1, name: "Holder", choice: 150, model_id: 1, reference: false }];
}
class IrModel extends models.Model {
    _name = "ir.model";
    name = fields.Char();
    model = fields.Char();
    _records = [
        { id: 1, name: "Option", model: "option" },
        { id: 2, name: "Holder", model: "holder" },
        { id: 3, name: "Model", model: "ir.model" },
    ];
}
defineModels([Option, Holder, IrModel]);

for (const widgetName of ["selection", "radio", "selection_badge", "statusbar"]) {
    test(`${widgetName}: retains the selected record beyond the normal result limit`, async () => {
        onRpc("option", ({ method, args, kwargs }) => {
            if (["name_search", "search_read"].includes(method)) {
                log.pipeline("choices RPC", { widgetName, method, args, kwargs });
            }
        });
        await mountView({
            type: "form",
            resModel: "holder",
            resId: 1,
            arch: `<form><field name="choice" widget="${widgetName}" options="{'clickable': True}"/></form>`,
        });
        if (widgetName === "selection") {
            expect(".o_field_widget[name=choice] input").toHaveValue("Option 150");
            await contains(".o_field_widget[name=choice] input").click();
            expect(".o_select_menu_item:contains(Option 150)").toHaveCount(1);
        } else if (widgetName === "radio") {
            expect(".o_field_widget[name=choice] input:checked").toHaveCount(1);
            expect(".o_radio_item:has(input:checked)").toHaveText("Option 150");
        } else if (widgetName === "selection_badge") {
            expect(".o_selection_badge.active").toHaveText("Option 150");
        } else {
            /** @type {any} */
            const value = controller.model.root.data.choice;
            expect(value.display_name).toBe("Option 150");
            // The mobile statusbar collapses to a toggler. Both layouts need
            // the current label in the options used by getCurrentLabel().
            expect(".o_statusbar_status").toHaveText(/Option 150/);
        }
    });
}

test("reference model lookup does not stamp a model selected after its request", async () => {
    const pending = new Deferred();
    const requested = [];
    /** @type {ReferenceField} */
    let widget;
    patchWithCleanup(ReferenceField.prototype, {
        setup() {
            super.setup();
            widget = this;
        },
    });
    onRpc("ir.model", "read", ({ args }) => {
        requested.push(...args[0]);
        log.pipeline("reference model lookup", { ids: args[0] });
        if (args[0].includes(2)) {
            return pending;
        }
    });
    await mountView({
        type: "form",
        resModel: "holder",
        resId: 1,
        arch: `<form><field name="model_id"/><field name="reference" options="{'model_field': 'model_id'}"/></form>`,
    });
    await controller.model.root.update({ model_id: { id: 2, display_name: "Holder" } });
    await animationFrame();
    expect(requested.includes(2)).toBe(true);
    await controller.model.root.update({ model_id: { id: 3, display_name: "Model" } });
    pending.resolve([{ id: 2, model: "holder" }]);
    for (let i = 0; i < 15; i++) {
        await Promise.resolve();
    }
    await animationFrame();
    await animationFrame();
    log.logic("reference model settled", {
        currentModelId: widget.currentModelId,
        relation: widget.getRelation(),
        requested,
    });
    expect(widget.currentModelId).toBe(3);
    expect(widget.getRelation()).toBe("ir.model");
    expect(requested.includes(3)).toBe(true);
});

// Include this file in normal mobile-lane discovery.
test.tags("mobile");
test("the selected status remains available in the collapsed mobile statusbar", async () => {
    patchWithCleanup(StatusBarField, { RELATION_LIMIT: 2 });
    await mountView({
        type: "form",
        resModel: "holder",
        resId: 1,
        arch: `<form><field name="choice" widget="statusbar" options="{'clickable': True}"/></form>`,
    });
    expect(".o_statusbar_status").toHaveText(/Option 150/);
});

for (const selected of /** @type {(number | false)[]} */ ([1, false])) {
    test(`selection: no fallback request is needed for selected=${selected}`, async () => {
        Holder._records[0].choice = selected;
        const requests = [];
        onRpc("option", "name_search", ({ args, kwargs }) => {
            requests.push({ args, kwargs });
            log.pipeline("ordinary choices", { args, kwargs });
        });
        await mountView({
            type: "form",
            resModel: "holder",
            resId: 1,
            arch: `<form><field name="choice" widget="selection"/></form>`,
        });
        await contains(".o_field_widget[name=choice] input").click();
        expect(".o_select_menu_item").toHaveCount(100);
        expect(requests).toHaveLength(1);
    });
}

for (const allowed of [true, false]) {
    test(`selection fallback preserves context and respects missing records: allowed=${allowed}`, async () => {
        let fallbacks = 0;
        onRpc("option", "name_search", ({ args, kwargs }) => {
            expect(kwargs.context.show_code).toBe(true);
            if (args[1]?.[0]?.[1] === "in") {
                fallbacks++;
                expect(args[1]).toEqual([["id", "in", [150]]]);
                expect(kwargs.limit).toBe(1);
                log.pipeline("selected fallback", { allowed, kwargs });
                return allowed ? [[150, "Context-specific label"]] : [];
            }
        });
        await mountView({
            type: "form",
            resModel: "holder",
            resId: 1,
            arch: `<form><field name="choice" widget="selection" context="{'show_code': True}"/></form>`,
        });
        expect(fallbacks).toBe(1);
        expect(".o_field_widget[name=choice] input").toHaveValue(
            allowed ? "Context-specific label" : "",
        );
        await contains(".o_field_widget[name=choice] input").click();
        expect(".o_select_menu_item").toHaveCount(allowed ? 101 : 100);
    });
}

test("reference model changes caused by pager navigation do not clear the next record", async () => {
    Holder._records[0].reference = "option,1";
    Holder._records.push({
        id: 2,
        name: "Next",
        choice: false,
        model_id: 2,
        reference: "holder,1",
    });
    await mountView({
        type: "form",
        resModel: "holder",
        resId: 1,
        resIds: [1, 2],
        arch: `<form><field name="model_id"/><field name="reference" options="{'model_field': 'model_id'}"/></form>`,
    });
    expect(".o_field_widget[name=reference] input").toHaveValue("Option 001");
    await contains(".o_pager_next").click();
    await animationFrame();
    log.logic("reference after navigation", {
        resId: controller.model.root.resId,
        reference: controller.model.root.data.reference,
    });
    expect(controller.model.root.resId).toBe(2);
    expect(controller.model.root.data.reference).not.toBe(false);
    expect(".o_field_widget[name=reference] input").toHaveValue("Holder");
});
