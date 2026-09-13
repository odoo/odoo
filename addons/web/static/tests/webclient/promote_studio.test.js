import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    getService,
    models,
    mountView,
    mountWithCleanup,
    patchWithCleanup,
    toggleKanbanColumnActions,
    webModels,
} from "@web/../tests/web_test_helpers";
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { PromoteStudioDialog } from "@web/webclient/promote_studio/promote_studio_dialog";
import { PromoteStudioSystrayItem } from "@web/webclient/promote_studio/promote_studio_systray_item";

class Partner extends models.Model {
    foo = fields.Char();
    bar = fields.Boolean();
    _records = [
        { id: 1, foo: "a", bar: true },
        { id: 2, foo: "b", bar: false },
    ];
}
defineModels({ ...webModels, Partner });

describe.current.tags("desktop");

test("the studio systray item is a system-user affordance that opens the upsell dialog", async () => {
    const item = registry.category("systray").get("PromoteStudioSystrayItem");
    patchWithCleanup(user, { isSystem: false });
    expect(item.isDisplayed()).toBe(false);
    patchWithCleanup(user, { isSystem: true });
    expect(item.isDisplayed()).toBe(true);

    await mountWithCleanup(PromoteStudioSystrayItem);
    await contains('button[title="Odoo Studio"]').click();
    expect(".o_dialog .modal-title").toHaveText(
        "Odoo Studio - Add new fields to any view",
    );
});

test("a kanban column offers Automations to an admin, and it upsells Studio when nothing installs it", async () => {
    patchWithCleanup(user, { isAdmin: true });
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });
    await toggleKanbanColumnActions(0);
    expect(".o-dropdown--menu .o_column_automations").toHaveCount(1);
    await contains(".o-dropdown--menu .o_column_automations").click();
    await animationFrame();
    expect(".o_dialog .modal-title").toHaveText(
        "Odoo Studio - Customize workflows in minutes",
    );
});

test("a kanban column does not offer Automations to a non-admin", async () => {
    patchWithCleanup(user, { isAdmin: false });
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });
    await toggleKanbanColumnActions(0);
    expect(".o-dropdown--menu").toHaveCount(1);
    expect(".o-dropdown--menu .o_column_automations").toHaveCount(0);
});

for (const stage of ["lookup", "install", "missing"]) {
    test(`Studio releases its UI block after ${stage} failure`, async () => {
        let dialog;
        patchWithCleanup(PromoteStudioDialog.prototype, {
            setup() {
                super.setup(...arguments);
                dialog = this;
            },
        });
        await mountWithCleanup(PromoteStudioSystrayItem);
        getService("dialog").add(PromoteStudioDialog, { title: "Studio" });
        await animationFrame();
        patchWithCleanup(dialog.ormService, {
            searchRead: async () => {
                if (stage === "lookup") {
                    throw new Error("lookup");
                }
                return stage === "missing" ? [] : [{ id: 1 }];
            },
            call: async () => {
                throw new Error("install");
            },
        });
        await expect(dialog.onClickInstallStudio()).rejects.toThrow();
        expect(getService("ui").blockCount).toBe(0);
        expect(dialog.disableClick).toBe(false);
    });
}

for (const stage of ["lookup", "install"]) {
    test(`closing Studio during ${stage} releases only its own UI block`, async () => {
        let dialog;
        const pending = new Deferred();
        patchWithCleanup(PromoteStudioDialog.prototype, {
            setup() {
                super.setup(...arguments);
                dialog = this;
            },
        });
        await mountWithCleanup(PromoteStudioSystrayItem);
        const close = getService("dialog").add(PromoteStudioDialog, {
            title: "Studio",
        });
        await animationFrame();
        patchWithCleanup(getService("orm"), {
            searchRead: async () => (stage === "lookup" ? pending : [{ id: 1 }]),
            call: async () => {
                expect.step("install");
                return pending;
            },
        });
        const ui = getService("ui");
        ui.block();
        dialog.onClickInstallStudio();
        await animationFrame();
        expect(ui.blockCount).toBe(2);
        close();
        await animationFrame();
        makeLogger("web.studio.test").lifecycle("closed while pending", {
            stage,
            blockCount: ui.blockCount,
        });
        expect(ui.blockCount).toBe(1);
        pending.resolve(stage === "lookup" ? [{ id: 1 }] : true);
        await animationFrame();
        expect(ui.blockCount).toBe(1);
        expect.verifySteps(stage === "install" ? ["install"] : []);
        ui.unblock();
    });
}
