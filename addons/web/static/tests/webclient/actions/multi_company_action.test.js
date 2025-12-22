import { beforeEach, expect, test } from "@odoo/hoot";
import { cookie } from "@web/core/browser/cookie";
import { redirect } from "@web/core/utils/urls";
import {
    defineModels,
    fields,
    getService,
    makeServerError,
    models,
    mountWebClient,
    onRpc,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { animationFrame } from "@odoo/hoot-dom";
import { browser } from "@web/core/browser/browser";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

class Partner extends models.Model {
    _name = "res.partner";

    name = fields.Char();

    _records = [{ id: 1, name: "First record" }];
    _views = {
        form: `
            <form>
                <group>
                    <field name="display_name"/>
                </group>
            </form>
        `,
    };
}

defineModels([Partner]);

beforeEach(() => {
    serverState.companies = [
        { id: 1, name: "Company 1", sequence: 1, parent_id: false, child_ids: [] },
        { id: 2, name: "Company 2", sequence: 2, parent_id: false, child_ids: [] },
        { id: 3, name: "Company 3", sequence: 3, parent_id: false, child_ids: [] },
    ];
    patchWithCleanup(browser.location, {
        reload() {
            expect.step("reload");
        },
    });
    patchWithCleanup(browser.location, {
        origin: "http://example.com",
    });
});

test("open record withtout the correct company (load state)", async () => {
    cookie.set("cids", "1");
    onRpc("web_read", () => {
        throw makeServerError({
            type: "AccessError",
            message: "Wrong Company",
            context: { suggested_company: { id: 2, display_name: "Company 2" } },
        });
    });

    redirect("/odoo/res.partner/1");
    await mountWebClient();
    expect(cookie.get("cids")).toBe("1-2");
    expect.verifySteps(["reload"]);
    expect(browser.location.href).toBe("http://example.com/odoo/res.partner/1", {
        message: "url did not change",
    });
});

test("open record withtout the correct company (doAction)", async () => {
    cookie.set("cids", "1");
    onRpc("web_read", () => {
        throw makeServerError({
            type: "AccessError",
            message: "Wrong Company",
            context: { suggested_company: { id: 2, display_name: "Company 2" } },
        });
    });

    await mountWebClient();
    getService("action").doAction({
        type: "ir.actions.act_window",
        res_id: 1,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await animationFrame();
    expect(cookie.get("cids")).toBe("1-2");
    expect.verifySteps(["reload"]);
    expect(browser.location.href).toBe("http://example.com/odoo/res.partner/1", {
        message: "url should contain the information of the doAction",
    });
});

test.tags("desktop");
test("form view in dialog shows wrong company error", async () => {
    expect.errors(1);
    cookie.set("cids", "1");

    onRpc("web_read", () => {
        throw makeServerError({
            type: "AccessError",
            message: "Wrong Company",
            context: { suggested_company: { id: 2, display_name: "Company 2" } },
        });
    });
    onRpc("has_group", () => true);
    Partner._views["list,false"] = `<list><field name="display_name"/></list>`;

    await mountWebClient();

    getService("dialog").add(FormViewDialog, {
        resModel: "res.partner",
        resId: 1,
    });
    await animationFrame();
    expect.verifyErrors(['Error: The following error occurred in onWillStart: "Wrong Company"']);
    expect(cookie.get("cids")).toBe("1"); // cookies were not modified
    expect.verifySteps([]); // don't reload
});
