// @ts-check

import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { BadgeSelectionWithIconsField } from "@mail/views/web/fields/badge_selection_icons/badge_selection_icons_field";
import { afterEach, beforeEach, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import {
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { enableLogging, getStatus, makeLogger } from "@web/core/debug/debug_logger";
import { FormController } from "@web/views/form/form_controller";

const log = makeLogger("web.field.badge_icons");
let previousLogSpec;
beforeEach(() => {
    previousLogSpec = getStatus().spec;
    enableLogging("web.field.*", { persist: false });
});
afterEach(() => enableLogging(previousLogSpec, { persist: false }));

class IconChoice extends models.Model {
    name = fields.Char();
    icon = fields.Char();
    _records = [
        { id: 1, name: "First", icon: "fa-check" },
        { id: 2, name: "Second", icon: "fa-star" },
    ];
}
class IconRecord extends models.Model {
    filter_id = fields.Integer({ default: 1 });
    choice = fields.Many2one({ relation: "icon.choice" });
    _records = [{ id: 1 }];
}
defineMailModels();
defineModels([IconChoice, IconRecord]);

test("icon badges reject an old choice while replacement data loads", async () => {
    /** @type {FormController} */
    let controller;
    /** @type {BadgeSelectionWithIconsField} */
    let widget;
    patchWithCleanup(FormController.prototype, {
        setup() {
            super.setup();
            controller = this;
        },
    });
    patchWithCleanup(BadgeSelectionWithIconsField.prototype, {
        setup() {
            super.setup();
            widget = this;
        },
    });
    const pending = new Deferred();
    onRpc("icon.choice", "search_read", ({ kwargs }) => {
        log.pipeline("load icon choices", { domain: kwargs.domain });
        if (kwargs.domain[0][2] === 2) {
            return pending;
        }
    });
    await mountView({
        type: "form",
        resModel: "icon.record",
        resId: 1,
        arch: `<form><field name="filter_id"/><field name="choice" widget="selection_badge_icons" iconField="icon" domain="[('id', '=', filter_id)]"/></form>`,
    });
    expect(".o_selection_badge").toHaveText("First");
    expect(".o_selection_badge .fa-check").toHaveCount(1);
    await controller.model.root.update({ filter_id: 2 });
    await animationFrame();
    expect(".o_selection_badge").toHaveAttribute("aria-disabled", "true");
    widget.onChange(1);
    expect(controller.model.root.data.choice).toBe(false);
    pending.resolve([{ id: 2, name: "Second", icon: "fa-star" }]);
    await animationFrame();
    expect(".o_selection_badge").toHaveText("Second");
    expect(".o_selection_badge .fa-star").toHaveCount(1);
    expect(".o_selection_badge").toHaveAttribute("aria-disabled", "false");
});

for (const [label, response, icon] of [
    [
        "named response properties",
        { icon: "fa-star", name: "Second", id: 2 },
        "fa-star",
    ],
    ["the default icon", { id: 2, name: "Second", icon: false }, "fa-check"],
]) {
    test(`icon badges use ${label}`, async () => {
        onRpc("icon.choice", "search_read", () => {
            log.pipeline("icon choice response", { response });
            return [response];
        });
        await mountView({
            type: "form",
            resModel: "icon.record",
            resId: 1,
            arch: `<form><field name="choice" widget="selection_badge_icons" iconField="icon"/></form>`,
        });
        expect(".o_selection_badge").toHaveText("Second");
        expect(`.o_selection_badge .${icon}`).toHaveCount(1);
        expect(".o_selection_badge").toHaveAttribute("value", "2");
    });
}
