import { expect, test } from "@odoo/hoot";
import { click, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame, runAllTimers, tick } from "@odoo/hoot-mock";
import {
    defineModels,
    editSearch,
    fields,
    getMockEnv,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { location } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { redirect } from "@web/core/utils/urls";

class ResConfigSettings extends models.Model {
    _name = "res.config.settings";
    bar = fields.Boolean();
}
defineModels([ResConfigSettings]);

test("Simple render", async () => {
    onRpc("/base_setup/demo_active", () => true);
    redirect("/odoo");
    await mountView({
        type: "form",
        arch: /* xml */ `
            <form js_class="base_settings">
                <app string="MyApp" name="my_app">
                    <widget name='res_config_dev_tool'/>
                </app>
            </form>`,
        resModel: "res.config.settings",
    });
    expect(router.current).toEqual({});
    expect(".o_widget_res_config_dev_tool").toHaveCount(1);
    expect(queryAllTexts`#developer_tool h2`).toEqual(["Developer Tools"]);
    expect(queryAllTexts`#developer_tool .o_setting_right_pane button`).toEqual([
        "Activate the developer mode",
        "Activate the developer mode (with assets)",
        "Activate the developer mode (with tests assets)",
    ]);
});

test("Activate the developer mode", async () => {
    onRpc("/base_setup/demo_active", () => true);
    patchWithCleanup(location, {
        reload() {
            expect.step("location reload");
        },
    });
    redirect("/odoo");
    await mountView({
        type: "form",
        arch: /* xml */ `
            <form js_class="base_settings">
                <app string="MyApp" name="my_app">
                    <widget name='res_config_dev_tool'/>
                </app>
            </form>`,
        resModel: "res.config.settings",
    });
    expect(router.current).toEqual({});
    await click("button:contains('Activate the developer mode')");
    await tick();
    expect(router.current).toEqual({ debug: 1 });
    expect.verifySteps(["location reload"]);
});

test("Activate the developer mode (with assets)", async () => {
    onRpc("/base_setup/demo_active", () => true);
    patchWithCleanup(location, {
        reload() {
            expect.step("location reload");
        },
    });
    redirect("/odoo");
    await mountView({
        type: "form",
        arch: /* xml */ `
            <form js_class="base_settings">
                <app string="MyApp" name="my_app">
                    <widget name='res_config_dev_tool'/>
                </app>
            </form>`,
        resModel: "res.config.settings",
    });
    expect(router.current).toEqual({});
    await click("button:contains('Activate the developer mode (with assets)')");
    await tick();
    expect(router.current).toEqual({ debug: "assets" });
    expect.verifySteps(["location reload"]);
});

test("Activate the developer mode (with tests assets)", async () => {
    onRpc("/base_setup/demo_active", () => true);
    patchWithCleanup(location, {
        reload() {
            expect.step("location reload");
        },
    });
    redirect("/odoo");
    await mountView({
        type: "form",
        arch: /* xml */ `
            <form js_class="base_settings">
                <app string="MyApp" name="my_app">
                    <widget name='res_config_dev_tool'/>
                </app>
            </form>`,
        resModel: "res.config.settings",
    });
    expect(router.current).toEqual({});

    await click("button:contains('Activate the developer mode (with tests assets)')");
    await tick();
    expect(router.current).toEqual({ debug: "assets,tests" });
    expect.verifySteps(["location reload"]);
});

test("Activate the developer modeddd (with tests assets)", async () => {
    serverState.debug = "assets,tests";
    onRpc("lazy_session_info", () => ({ is_demo: true }));
    patchWithCleanup(location, {
        reload() {
            expect.step("location reload");
        },
    });
    redirect("/odoo?debug=assets%2Ctests");
    await mountView({
        type: "form",
        arch: /* xml */ `
            <form js_class="base_settings">
                <app string="MyApp" name="my_app">
                    <widget name='res_config_dev_tool'/>
                </app>
            </form>`,
        resModel: "res.config.settings",
    });
    getMockEnv().bus.trigger("WEB_CLIENT_READY");
    await animationFrame();
    expect(router.current).toEqual({ debug: "assets,tests" });

    expect(queryAllTexts`#developer_tool .o_setting_right_pane button`).toEqual([
        "Deactivate the developer mode",
    ]);

    await click("button:contains('Deactivate the developer mode')");
    await tick();
    expect(router.current).toEqual({ debug: 0 });
    expect.verifySteps(["location reload"]);
});

test("Developer Tools block is hidden when the search matches nothing in it", async () => {
    onRpc("/base_setup/demo_active", () => true);
    redirect("/odoo");
    await mountView({
        type: "form",
        arch: /* xml */ `
            <form js_class="base_settings">
                <app string="MyApp" name="my_app">
                    <widget name='res_config_dev_tool'/>
                    <block title="Other block">
                        <setting help="this is bar">
                            <field name="bar"/>
                        </setting>
                    </block>
                </app>
            </form>`,
        resModel: "res.config.settings",
    });
    expect(queryAllTexts`#developer_tool h2:not(.d-none)`).toEqual(["Developer Tools"]);

    // This block is the one case that nothing else re-renders on a search: it
    // holds no SearchableSetting, so nothing inside it reads the search value,
    // and it is instantiated by a widget template rather than by the settings
    // compiler, so no parent re-renders it either. It hides only because
    // `useLayoutEffect` reads its dependencies from a render, which subscribes
    // the block itself — see the comment in `settings_block.js`.
    await editSearch("bar");
    await runAllTimers();
    await animationFrame();
    expect(queryAllTexts`#developer_tool h2:not(.d-none)`).toEqual([]);
    expect("#developer_tool .o_settings_container").toHaveClass("d-none");
    expect(queryAllTexts`.settings h2:not(.d-none)`).toEqual(["Other block"]);

    await editSearch("");
    await runAllTimers();
    await animationFrame();
    expect(queryAllTexts`#developer_tool h2:not(.d-none)`).toEqual(["Developer Tools"]);
});
