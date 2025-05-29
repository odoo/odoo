import { after, beforeEach, expect, getFixture, test } from "@odoo/hoot";
import {
    click,
    edit,
    on,
    queryAllProperties,
    queryAllTexts,
    queryFirst,
    resize,
    unload,
} from "@odoo/hoot-dom";
import { animationFrame, Deferred, mockSendBeacon, mockTouch, runAllTimers } from "@odoo/hoot-mock";
import {
    clickModalButton,
    clickSave,
    defineActions,
    defineModels,
    editSearch,
    fields,
    getService,
    hideTab,
    makeServerError,
    mockService,
    models,
    mountView,
    mountWebClient,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    serverState,
    stepAllNetworkCalls,
    swipeLeft,
    swipeRight,
} from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { rpc } from "@web/core/network/rpc";
import { RPCCache } from "@web/core/network/rpc_cache";
import { pick } from "@web/core/utils/objects";
import { redirect } from "@web/core/utils/urls";
import { SettingsFormCompiler } from "@web/webclient/settings_form_view/settings_form_compiler";
import { WebClient } from "@web/webclient/webclient";

const MOCK_IMAGE =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z9DwHwAGBQKA3H7sNwAAAABJRU5ErkJggg==";

class ResConfigSettings extends models.Model {
    _name = "res.config.settings";

    foo = fields.Boolean();
    bar = fields.Boolean();
    task_id = fields.Many2one({ relation: "task", default: 100 });
    file = fields.Binary({
        relation: "task",
        related: "task_id.file",
        default: "coucou==\n",
    });
    file_name = fields.Char({
        related: "task_id.file_name",
        default: "coucou.txt",
    });
    tasks = fields.One2many({ relation: "task" });
    baz = fields.Selection({
        string: "Baz",
        selection: [
            [1, "treads"],
            [2, "treats"],
        ],
        default: 1,
    });

    execute() {}
}

class Task extends models.Model {
    name = fields.Char();
    file = fields.Binary();
    file_name = fields.Char();

    _records = [{ id: 100, file: "coucou==\n", file_name: "coucou.txt" }];
}

class Project extends models.Model {
    foo = fields.Boolean({ string: "Foo" });
    bar = fields.Boolean({ string: "Bar" });
}

defineModels([ResConfigSettings, Task, Project]);

beforeEach(() => {
    patchWithCleanup(SettingsFormCompiler.prototype, {
        compileApp(el, params) {
            el.setAttribute("logo", MOCK_IMAGE);
            return super.compileApp(el, params);
        },
    });
});

test.tags("desktop");
test("change setting on nav bar click in base settings on desktop", async () => {
    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="CRM" name="crm">
                    <setting type="header" string="Foo">
                        <field name="foo" title="Foo?."/>
                        <button name="nameAction" type="object" string="Button" class="btn btn-link"/>
                    </setting>
                    <block title="Title of group Bar">
                        <setting help="this is bar" info="this is bar info" documentation="/applications/technical/web/settings/this_is_a_test.html">
                            <field name="bar"/>
                            <button name="buttonName" icon="oi-arrow-right" type="action" string="Manage Users" class="btn-link"/>
                        </setting>
                        <setting>
                            <label string="Big BAZ" for="baz"/>
                            <div class="text-muted">this is a baz</div>
                            <field name="baz"/>
                            <label>label with content</label>
                        </setting>
                    </block>
                    <block title="Title of group Foo">
                        <setting help="this is foo" info="this is foo info" documentation="https://www.odoo.com/documentation/1.0/applications/technical/web/settings/this_is_another_test.html">
                            <field name="foo"/>
                        </setting>
                        <setting string="Personalize setting" help="this is full personalize setting">
                            <div>This is a different setting</div>
                        </setting>
                    </block>
                    <block title="Hide group Foo" invisible="not bar">
                        <setting string="Hide Foo" help="this is hide foo">
                            <field name="foo"/>
                        </setting>
                    </block>
                </app>
            </form>
        `,
    });

    expect(".selected").toHaveAttribute("data-key", "crm", { message: "crm setting selected" });
    expect(".settings .app_settings_block").toBeVisible({
        message: "res.config.settings settings show",
    });
    expect(queryAllTexts(".settings .o_settings_container .o_form_label")).toEqual([
        "Bar",
        "Big BAZ",
        "Foo",
        "Personalize setting",
    ]);
    expect(queryAllTexts(".settings .text-muted")).toEqual([
        "this is bar",
        "this is a baz",
        "this is foo",
        "this is full personalize setting",
    ]);
    expect(queryAllTexts(".settings h2:not(.d-none)")).toEqual([
        "Title of group Bar",
        "Title of group Foo",
    ]);
    expect(".o_form_editable").not.toHaveClass("o_form_nosheet");
    expect(".o_searchview input").toBeFocused({ message: "searchview input should be focused" });
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(1);
    expect(".o_setting_box a").toHaveCount(2);
    expect(".o_setting_box span.fa:eq(0)").toHaveAttribute(
        "title",
        "this is bar info"
    );
    expect(".o_setting_box span.fa:eq(1)").toHaveAttribute(
        "title",
        "this is foo info"
    );
    expect(".o_setting_box a:eq(0)").toHaveAttribute(
        "href",
        "https://www.odoo.com/documentation/1.0/applications/technical/web/settings/this_is_a_test.html"
    );
    expect(".o_setting_box a:eq(1)").toHaveAttribute(
        "href",
        "https://www.odoo.com/documentation/1.0/applications/technical/web/settings/this_is_another_test.html"
    );

    await editSearch("Hello there");
    expect(".o_searchview input").toHaveValue("Hello there", {
        message: "input value should be updated",
    });
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(0);

    await editSearch("b");
    expect(queryFirst(".highlighter")).toHaveText("B", { message: "b word highlighted" });
    expect(queryAllTexts(".o_settings_container .o_setting_box .o_form_label")).toEqual(
        ["Bar", "Big BAZ"],
        { message: "Foo is not shown" }
    );

    expect(queryAllTexts(".settings h2:not(.d-none)")).toEqual(["Title of group Bar"], {
        message: "The title of group Bar is also selected",
    });
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(1);

    await editSearch("Big");
    expect(queryAllTexts(".o_settings_container  .o_setting_box .o_form_label")).toEqual(
        ["Big BAZ"],
        { message: "Only 'Big Baz' is shown" }
    );
    expect(queryAllTexts(".settings h2:not(.d-none)")).toEqual(["Title of group Bar"], {
        message: "The title of group Bar is also selected",
    });
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(1);

    await editSearch("Manage Us");
    expect(queryFirst(".highlighter")).toHaveText("Manage Us", {
        message: "Manage Us word highlighted",
    });
    expect(queryAllTexts(".o_settings_container .o_setting_box .o_form_label")).toEqual(["Bar"], {
        message: "Foo is not shown",
    });
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(1);

    await editSearch("group Bar");
    expect(queryAllTexts(".o_settings_container .o_setting_box .o_form_label")).toEqual(
        ["Bar", "Big BAZ"],
        { message: "When searching a title, all group is shown" }
    );
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(1);

    await editSearch("different");
    expect(queryAllTexts(".o_settings_container .o_setting_box .o_form_label")).toEqual(
        ["Personalize setting"],
        { message: "When searching a title, all group is shown" }
    );
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(1);

    await editSearch("bx");
    await animationFrame();
    expect(".o_nocontent_help").toBeVisible({ message: "record not found message shown" });
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(0);

    await editSearch("Fo");
    expect(queryFirst(".highlighter")).toHaveText("Fo", { message: "Fo word highlighted" });
    expect(queryAllTexts(".o_settings_container .o_setting_box .o_form_label")).toEqual(
        ["Foo", "Personalize setting"],
        { message: "only settings in group Foo is shown" }
    );
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(1);

    await editSearch("Hide");
    expect(queryAllTexts(".settings h2:not(.d-none)")).toEqual([], {
        message: "Hide settings should not be shown",
    });
    expect(queryAllTexts(".o_settings_container  .o_setting_box .o_form_label")).toEqual([], {
        message: "Hide settings should not be shown",
    });
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(0);
});

test.tags("mobile");
test("change setting on nav bar click in base settings on mobile", async () => {
    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="CRM" name="crm">
                    <setting type="header" string="Foo">
                        <field name="foo" title="Foo?."/>
                        <button name="nameAction" type="object" string="Button" class="btn btn-link"/>
                    </setting>
                    <block title="Title of group Bar">
                        <setting help="this is bar" info="this is bar info" documentation="/applications/technical/web/settings/this_is_a_test.html">
                            <field name="bar"/>
                            <button name="buttonName" icon="oi-arrow-right" type="action" string="Manage Users" class="btn-link"/>
                        </setting>
                        <setting>
                            <label string="Big BAZ" for="baz"/>
                            <div class="text-muted">this is a baz</div>
                            <field name="baz"/>
                            <label>label with content</label>
                        </setting>
                    </block>
                    <block title="Title of group Foo">
                        <setting help="this is foo" info="this is foo info" documentation="https://www.odoo.com/documentation/1.0/applications/technical/web/settings/this_is_another_test.html">
                            <field name="foo"/>
                        </setting>
                        <setting string="Personalize setting" help="this is full personalize setting">
                            <div>This is a different setting</div>
                        </setting>
                    </block>
                    <block title="Hide group Foo" invisible="not bar">
                        <setting string="Hide Foo" help="this is hide foo">
                            <field name="foo"/>
                        </setting>
                    </block>
                </app>
            </form>
        `,
    });

    expect(".selected").toHaveAttribute("data-key", "crm", { message: "crm setting selected" });
    expect(".settings .app_settings_block").toBeVisible({
        message: "res.config.settings settings show",
    });
    expect(queryAllTexts(".settings .o_settings_container .o_form_label")).toEqual([
        "Bar",
        "Big BAZ",
        "Foo",
        "Personalize setting",
    ]);
    expect(queryAllTexts(".settings .text-muted")).toEqual([
        "this is bar",
        "this is a baz",
        "this is foo",
        "this is full personalize setting",
    ]);
    expect(queryAllTexts(".settings h2:not(.d-none)")).toEqual([
        "Title of group Bar",
        "Title of group Foo",
    ]);
    expect(".o_form_editable").not.toHaveClass("o_form_nosheet");
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(1);
    expect(".o_setting_box a").toHaveCount(2);
    expect(".o_setting_box span.fa:eq(0)").toHaveAttribute(
        "title",
        "this is bar info"
    );
    expect(".o_setting_box span.fa:eq(1)").toHaveAttribute(
        "title",
        "this is foo info"
    );
    expect(".o_setting_box a:eq(0)").toHaveAttribute(
        "href",
        "https://www.odoo.com/documentation/1.0/applications/technical/web/settings/this_is_a_test.html"
    );
    expect(".o_setting_box a:eq(1)").toHaveAttribute(
        "href",
        "https://www.odoo.com/documentation/1.0/applications/technical/web/settings/this_is_another_test.html"
    );

    await editSearch("Hello there");
    expect(".o_searchview input").toHaveValue("Hello there", {
        message: "input value should be updated",
    });
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(0);

    await editSearch("b");
    expect(queryFirst(".highlighter")).toHaveText("B", { message: "b word highlighted" });
    expect(queryAllTexts(".o_settings_container .o_setting_box .o_form_label")).toEqual(
        ["Bar", "Big BAZ"],
        { message: "Foo is not shown" }
    );

    expect(queryAllTexts(".settings h2:not(.d-none)")).toEqual(["Title of group Bar"], {
        message: "The title of group Bar is also selected",
    });
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(1);

    await editSearch("Big");
    expect(queryAllTexts(".o_settings_container  .o_setting_box .o_form_label")).toEqual(
        ["Big BAZ"],
        { message: "Only 'Big Baz' is shown" }
    );
    expect(queryAllTexts(".settings h2:not(.d-none)")).toEqual(["Title of group Bar"], {
        message: "The title of group Bar is also selected",
    });
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(1);

    await editSearch("Manage Us");
    expect(queryFirst(".highlighter")).toHaveText("Manage Us", {
        message: "Manage Us word highlighted",
    });
    expect(queryAllTexts(".o_settings_container .o_setting_box .o_form_label")).toEqual(["Bar"], {
        message: "Foo is not shown",
    });
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(1);

    await editSearch("group Bar");
    expect(queryAllTexts(".o_settings_container .o_setting_box .o_form_label")).toEqual(
        ["Bar", "Big BAZ"],
        { message: "When searching a title, all group is shown" }
    );
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(1);

    await editSearch("different");
    expect(queryAllTexts(".o_settings_container .o_setting_box .o_form_label")).toEqual(
        ["Personalize setting"],
        { message: "When searching a title, all group is shown" }
    );
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(1);

    await editSearch("bx");
    await animationFrame();
    expect(".o_nocontent_help").toBeVisible({ message: "record not found message shown" });
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(0);

    await editSearch("Fo");
    expect(queryFirst(".highlighter")).toHaveText("Fo", { message: "Fo word highlighted" });
    expect(queryAllTexts(".o_settings_container .o_setting_box .o_form_label")).toEqual(
        ["Foo", "Personalize setting"],
        { message: "only settings in group Foo is shown" }
    );
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(1);

    await editSearch("Hide");
    expect(queryAllTexts(".settings h2:not(.d-none)")).toEqual([], {
        message: "Hide settings should not be shown",
    });
    expect(queryAllTexts(".o_settings_container  .o_setting_box .o_form_label")).toEqual([], {
        message: "Hide settings should not be shown",
    });
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(0);
});

test("edit header field", async () => {
    expect.assertions(15);
    ResConfigSettings._fields.foo_text = fields.Char();

    const records = {
        1: {
            foo_text: "First default value",
        },
        2: {
            foo_text: "Second default value",
        },
    };

    let lastRecordSaved;

    ResConfigSettings._onChanges.baz = (record) => {
        Object.assign(record, records[record.baz]);
    };

    onRpc("web_save", ({ args }) => {
        lastRecordSaved = args[1];
    });
    onRpc("execute", ({ args }) => {
        expect(args[0].length).toBe(1);
        records[lastRecordSaved.baz].foo_text = lastRecordSaved.foo_text;
        return true;
    });

    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="CRM" name="crm">
                    <setting type="header" string="Type">
                        <field name="baz" title="Make a choice" widget="radio"/>
                    </setting>
                    <block title="Title of group Bar">
                        <setting documentation="/applications/technical/web/settings/this_is_a_test.html">
                            <field name="foo_text"/>
                        </setting>
                    </block>
                </app>
            </form>
        `,
    });
    expect(queryAllProperties("[name='baz'] input", "checked")).toEqual([true, false]);
    expect(queryFirst("[name='foo_text'] input")).toHaveValue("First default value");

    // edit a header field with no other changes
    await click("[name='baz'] input:eq(1)");
    await animationFrame();
    expect(".modal").toHaveCount(0);
    expect(queryAllProperties("[name='baz'] input", "checked")).toEqual([false, true]);
    expect("[name='foo_text'] input").toHaveValue("Second default value");

    // edit a header field with other changes
    await click("[name='foo_text'] input");
    await edit("Hello");
    await animationFrame();
    await click("[name='baz'] input:eq(0)");
    await animationFrame();
    expect(".modal").toHaveCount(1);

    // Stay here
    await click(".modal .btn-secondary");
    await animationFrame();
    expect(queryAllProperties("[name='baz'] input", "checked")).toEqual([false, true]);
    expect("[name='foo_text'] input").toHaveValue("Hello");

    await click("[name='baz'] input:eq(0)");
    await animationFrame();
    expect(".modal").toHaveCount(1);

    // Discard
    await click(".modal .btn-secondary:eq(1)");
    await animationFrame();
    expect(queryAllProperties("[name='baz'] input", "checked")).toEqual([true, false]);
    expect("[name='foo_text'] input").toHaveValue("First default value");

    await click("[name='foo_text'] input");
    await edit("Hello again");
    await animationFrame();
    await click("[name='baz'] input:eq(1)");
    await animationFrame();
    expect(".modal").toHaveCount(1);

    // Save
    await click(".modal .btn-primary");
    await animationFrame();
    expect(queryAllProperties("[name='baz'] input", "checked")).toEqual([true, false]);
    expect("[name='foo_text'] input").toHaveValue("Hello again");
});

test("don't show noContentHelper if no search is done", async () => {
    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="CRM" name="crm">
                    <block title="Setting title" help="Settings will appear below">
                        <div/>
                    </block>
                </app>
            </form>`,
    });
    expect(".o_nocontent_help").not.toHaveCount();
});

test("unhighlight section not matching anymore", async () => {
    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="CRM" name="crm">
                    <block title="Baz">
                        <field name="baz" class="o_light_label" widget="radio"/>
                    </block>
                </app>
            </form>
        `,
    });
    expect(".selected").toHaveAttribute("data-key", "crm", { message: "crm setting selected" });
    expect(".settings .app_settings_block").toBeVisible({ message: "project settings show" });

    await editSearch("trea");
    await runAllTimers();
    await animationFrame();
    expect(".highlighter").toHaveCount(2, { message: "should have 2 options highlighted" });
    expect(queryAllTexts(":has(>.highlighter)")).toEqual(["treads", "treats"]);

    await editSearch("tread");
    await runAllTimers();
    await animationFrame();
    expect(".highlighter").toHaveCount(1, { message: "should have only one highlighted" });
    expect(queryAllTexts(":has(>.highlighter)")).toEqual(["treads"]);
});

test("hide / show setting tips properly", async () => {
    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="Settings" name="settings">
                    <block title="Setting Header" help="Settings will appear below">
                        <setting help="this is bar">
                            <field name="bar"/>
                        </setting>
                    </block>
                    <block title="Title of group Foo">
                        <setting help="this is foo">
                            <field name="foo"/>
                        </setting>
                    </block>
                </app>
            </form>
        `,
    });
    expect(".o_setting_tip:not(.d-none)").toHaveCount(1, {
        message: "Tip should not be hidden initially",
    });

    await editSearch("below");
    await runAllTimers();
    await animationFrame();
    expect(".o_setting_tip:not(.d-none)").toHaveCount(1, {
        message: "Tip should not be hidden",
    });
    await editSearch("Foo");
    await runAllTimers();
    await animationFrame();
    expect(".o_setting_tip:not(.d-none)").toHaveCount(0, {
        message: "Tip should not be displayed",
    });
    await editSearch("");
    await runAllTimers();
    await animationFrame();
    expect(".o_setting_tip:not(.d-none)").toHaveCount(1, {
        message: "Tip should not be hidden",
    });
});

test.tags("desktop");
test("settings views does not read existing id when coming back in breadcrumbs", async () => {
    expect.assertions(4);
    onRpc("has_group", () => true);
    defineActions([
        {
            id: 1,
            name: "Settings view",
            res_model: "res.config.settings",
            views: [[false, "form"]],
        },
        {
            id: 4,
            name: "Other action",
            res_model: "task",
            views: [[false, "list"]],
        },
    ]);

    ResConfigSettings._views.form = /* xml */ `
        <form string="Settings" js_class="base_settings">
            <app string="CRM" name="crm">
                <block>
                    <setting help="this is foo">
                        <field name="foo"/>
                    </setting>
                </block>
                <button name="4" string="Execute action" type="action"/>
            </app>
        </form>
    `;
    Task._views.list = /* xml */ `
        <list>
            <field name="display_name"/>
        </list>
    `;
    onRpc(({ method }) => {
        if (method && method !== "has_group") {
            expect.step(method);
        }
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(".o_field_boolean input").toHaveProperty("disabled", false);
    await click("button[name='4']");
    await animationFrame();
    expect(".breadcrumb").toHaveText("Settings");
    await click(".o_control_panel .breadcrumb-item a");
    await animationFrame();
    expect(".o_field_boolean input").toHaveProperty("disabled", false);
    expect.verifySteps([
        "get_views", // initial setting action
        "onchange", // this is a setting view => new record transient record
        "web_save", // create the record before doing the action
        "get_views", // for other action in breadcrumb,
        "web_search_read", // with a searchread
        "onchange", // when we come back, we want to restart from scratch
    ]);
});

test("resIds should contains only 1 id", async () => {
    expect.assertions(1);
    ResConfigSettings._fields.foo_text = fields.Char({
        translate: true,
    });

    serverState.lang = "en_US";
    serverState.multiLang = true;

    onRpc("get_installed", () => [
        ["en_US", "English"],
        ["fr_BE", "French (Belgium)"],
    ]);
    onRpc("get_field_translations", () => [
        [
            {
                lang: "en_US",
                source: "My little Foo Value",
                value: "My little Foo Value",
            },
            {
                lang: "fr_BE",
                source: "My little Foo Value",
                value: "Valeur de mon petit Foo",
            },
        ],
        {
            translation_type: "char",
            translation_show_source: true,
        },
    ]);
    onRpc("execute", ({ args }) => {
        expect(args[0].length).toBe(1);
        return true;
    });

    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <div class="o_setting_container">
                    <div class="settings">
                        <app string="CRM" name="crm">
                            <block>
                                <setting title="Foo Text">
                                    <field name="foo_text"/>
                                </setting>
                            </block>
                        </app>
                    </div>
                </div>
            </form>
        `,
    });

    await click(".o_field_char .btn.o_field_translate"); // Translate
    await animationFrame();
    await click(".modal-footer .btn:eq(1)"); // Discard
    await animationFrame();
    await clickSave(); // Save Settings
});

test("settings views does not read existing id when reload", async () => {
    defineActions([
        {
            id: 1,
            name: "Settings view",
            res_model: "res.config.settings",
            views: [[1, "form"]],
        },
        {
            id: 4,
            name: "Other action",
            res_model: "task",
            target: "new",
            views: [["view_ref", "form"]],
        },
    ]);
    ResConfigSettings._views["form,1"] = /* xml */ `
        <form string="Settings" js_class="base_settings">
            <app string="CRM" name="crm">
                <block>
                    <setting title="Foo" help="this is foo">
                        <field name="foo"/>
                    </setting>
                </block>
                <button name="4" string="Execute action" type="action"/>
            </app>
        </form>
    `;
    Task._views["form,view_ref"] = /* xml */ `
        <form>
            <field name="display_name"/>
        </form>
    `;

    onRpc(({ method }) => {
        expect.step(method);
    });

    await mountWithCleanup(WebClient);

    await getService("action").doAction(1);

    expect.verifySteps([
        "get_views", // initial setting action
        "onchange", // this is a setting view => new record transient record
    ]);

    await click("button[name='4']");
    await animationFrame();

    expect.verifySteps([
        "web_save", // settings: create the record before doing the action
        "get_views", // dialog: get views
        "onchange", // dialog: onchange
    ]);

    await click(".modal button.btn.btn-primary.o_form_button_save");
    await animationFrame();

    expect.verifySteps([
        "web_save", // dialog: create the record before doing back to the settings
        "onchange", // settings: when we come back, we want to restart from scratch
    ]);
});

test("settings views ask for confirmation when leaving if dirty", async () => {
    defineActions([
        {
            id: 1,
            name: "Settings view",
            res_model: "res.config.settings",
            views: [[false, "form"]],
        },
        {
            id: 4,
            name: "Other action",
            res_model: "task",
            views: [[false, "form"]],
        },
    ]);
    ResConfigSettings._views.form = /* xml */ `
        <form string="Settings" js_class="base_settings">
            <app string="CRM" name="crm">
                <block>
                    <setting label="Foo" help="this is foo">
                        <field name="foo"/>
                    </setting>
                </block>
            </app>
        </form>
    `;
    Task._views.form = /* xml */ `
        <form>
            <field name="display_name"/>
        </form>
    `;

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    const action = getService("action").doAction(1);
    await animationFrame();
    expect(".modal").toHaveCount(0, { message: "do not open modal if there is no change" });
    await action;

    await getService("action").doAction(1);
    await click(".o_field_boolean input");
    await animationFrame();
    getService("action").doAction(4);
    await animationFrame();
    expect(".modal").toHaveCount(1, { message: "open modal if there is change" });
    expect(".modal-title").toHaveText("Unsaved changes");
});

test("Auto save: don't save on closing tab/browser", async () => {
    mockSendBeacon(() => expect.step("sendBeacon"));
    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="Base Setting" name="base-setting">
                    <setting>
                        <field name="bar"/>Make Changes
                    </setting>
                </app>
            </form>
        `,
    });

    expect(".o_field_boolean input:checked").toHaveCount(0, {
        message: "checkbox should not be checked",
    });
    expect(".o_dirty_warning").toHaveCount(0, { message: "warning message should not be shown" });
    await click(".o_field_boolean input[id=bar_0]");
    await animationFrame();
    expect(".o_field_boolean input:checked").toHaveCount(1, {
        message: "checkbox should be checked",
    });

    await unload();
    await animationFrame();
    expect.verifySteps([]);
});

test("Auto save: don't save on visibility change", async () => {
    onRpc("web_save", () => expect.step("should not call web_save"));
    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="Base Setting" name="base-setting">
                    <setting>
                        <field name="bar"/>Make Changes
                    </setting>
                </app>
            </form>
        `,
    });

    expect(".o_field_boolean input:checked").toHaveCount(0, {
        message: "checkbox should not be checked",
    });
    expect(".o_dirty_warning").toHaveCount(0, { message: "warning message should not be shown" });
    click(".o_field_boolean input[id=bar_0]");
    await animationFrame();
    expect(".o_field_boolean input:checked").toHaveCount(1, {
        message: "checkbox should be checked",
    });

    await hideTab();
    await animationFrame();
    expect.verifySteps([]);
});

test("correctly copy attributes to compiled labels", async () => {
    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form string="Settings" js_class="base_settings">
                <app string="CRM" name="crm">
                    <block>
                        <setting>
                            <label for="foo" string="Label Before" class="a"/>
                            <field name="foo" class="b"/>
                            <label for="foo" string="Label After" class="c"/>
                        </setting>
                    </block>
                </app>
            </form>
        `,
    });

    expect(".o_form_label:eq(0)").toHaveClass("a");
    expect(".o_field_widget.o_field_boolean").toHaveClass("b");
    expect(".o_form_label:eq(1)").toHaveClass("c");
});

test("settings views does not write the id on the url", async () => {
    defineActions([
        {
            id: 1,
            name: "Settings view",
            path: "settings",
            res_model: "res.config.settings",
            views: [[false, "form"]],
        },
    ]);
    ResConfigSettings._views.form = /* xml */ `
        <form string="Settings" js_class="base_settings">
            <app string="CRM" name="crm">
                <block>
                    <setting help="this is foo">
                        <field name="foo"/>
                    </setting>
                </block>
            </app>
        </form>
    `;
    Task._views.list = /* xml */ `
        <list>
            <field name="display_name"/>
        </list>
    `;

    await mountWithCleanup(WebClient);

    await getService("action").doAction(1);
    await runAllTimers();
    expect(browser.location.pathname).toBe("/odoo/settings");
    expect(".o_field_boolean input").toHaveProperty("disabled", false);
    await click(".o_field_boolean input");
    await animationFrame();
    expect(".o_field_boolean input").toBeChecked({ message: "checkbox should be checked" });
    await clickSave();

    await animationFrame();
    expect(router.current.resId).toBe(undefined);
    expect(browser.location.pathname).toBe("/odoo/settings");
});

test.tags("desktop");
test("settings views can search when coming back in breadcrumbs", async () => {
    onRpc("has_group", () => true);
    defineActions([
        {
            id: 1,
            name: "Settings view",
            res_model: "res.config.settings",
            views: [[false, "form"]],
        },
        {
            id: 4,
            name: "Other action",
            res_model: "task",
            views: [[false, "list"]],
        },
    ]);
    ResConfigSettings._views.form = /* xml */ `
        <form string="Settings" js_class="base_settings">
            <app string="CRM" name="crm">
                <block>
                    <setting help="this is foo">
                        <field name="foo"/>
                    </setting>
                </block>
                <button name="4" string="Execute action" type="action"/>
            </app>
        </form>
    `;
    Task._views.list = /* xml */ `
        <list>
            <field name="display_name"/>
        </list>
    `;

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    await click("button[name='4']");
    await animationFrame();
    await click(".o_control_panel .breadcrumb-item a");
    await animationFrame();
    await editSearch("Fo");
    await runAllTimers();
    expect(queryFirst(".highlighter")).toHaveText("Fo", { message: "Fo word highlighted" });
});

test("search for default label when label has empty string", async () => {
    onRpc("has_group", () => true);
    defineActions([
        {
            id: 1,
            name: "Settings view",
            res_model: "res.config.settings",
            views: [[false, "form"]],
        },
        {
            id: 4,
            name: "Other action",
            res_model: "task",
            views: [[false, "list"]],
        },
    ]);
    ResConfigSettings._views.form = /* xml */ `
        <form string="Settings" js_class="base_settings">
            <app string="CRM" name="crm">
                <block>
                    <setting>
                        <label for="foo" string=""/>
                        <field name="foo"/>
                    </setting>
                </block>
            </app>
        </form>
    `;
    Task._views.list = /* xml */ `
        <list>
            <field name="display_name"/>
        </list>
    `;

    await mountWithCleanup(WebClient);

    await getService("action").doAction(1);
    expect(".o_form_label").toHaveCount(1);
    expect(".o_form_label").toHaveText("");
    expect(".app_settings_block:not(.d-none) .settingSearchHeader").toHaveCount(0);
    await editSearch("Fo");
    await runAllTimers();
    expect(".o_form_label").toHaveCount(0);
    expect(".app_settings_block:not(.d-none) .settingSearchHeader").toHaveCount(0);
});

test("clicking on any button in setting should show discard warning if setting form is dirty", async () => {
    onRpc("has_group", () => true);
    defineActions([
        {
            id: 1,
            name: "Settings view",
            res_model: "res.config.settings",
            views: [[false, "form"]],
        },
        {
            id: 4,
            name: "Other action",
            res_model: "task",
            views: [[false, "list"]],
        },
    ]);

    ResConfigSettings._views.form = /* xml */ `
        <form string="Settings" js_class="base_settings">
            <app string="CRM" name="crm">
                <block>
                    <setting string="Foo" help="this is foo">
                        <field name="foo"/>
                    </setting>
                </block>
                <button name="4" string="Execute action" type="action"/>
            </app>
        </form>
    `;
    Task._views.list = /* xml */ `
        <list>
            <field name="display_name"/>
        </list>
    `;

    onRpc("/web/dataset/call_button/*/<string:method>", async (request, { method }) => {
        expect.step(method);
    });

    await mountWithCleanup(WebClient);

    await getService("action").doAction(1);
    expect(".o_field_boolean input:checked").toHaveCount(0, {
        message: "checkbox should not be checked",
    });

    await click(".o_field_boolean input");
    await animationFrame();
    expect(".o_field_boolean input").toBeChecked({ message: "checkbox should be checked" });

    await click("button[name='4']");
    await animationFrame();
    expect(".modal").toHaveCount(1, { message: "should open a warning dialog" });

    await clickModalButton({ text: "Discard" });
    await animationFrame();

    expect(".o_list_view").toHaveCount(1, { message: "should be open list view" });
    await click(".o_control_panel .breadcrumb-item a, .o_back_button");
    await animationFrame();
    expect(".o_field_boolean input:checked").toHaveCount(0, {
        message: "checkbox should not be checked",
    });

    await click(".o_field_boolean input");
    await animationFrame();
    await click("button[name='4']");
    await animationFrame();
    expect(".modal").toHaveCount(1, { message: "should open a warning dialog" });

    await clickModalButton({ text: "Stay Here" });
    expect(".o_form_view").toHaveCount(1, { message: "should be remain on form view" });

    await clickSave();
    expect(".modal").toHaveCount(0, { message: "should not open a warning dialog" });
    expect(".o_field_boolean input").toHaveProperty("disabled", false); // Everything must stay in edit

    await click(".o_field_boolean input");
    await animationFrame();
    await click(".o_control_panel .o_form_button_cancel"); // Form Discard button
    await animationFrame();
    expect(".modal").toHaveCount(0, { message: "should not open a warning dialog" });

    expect.verifySteps(["execute"]);
});

test("header field don't dirty settings", async () => {
    onRpc("has_group", () => true);
    expect.assertions(6);

    defineActions([
        {
            id: 1,
            name: "Settings view",
            res_model: "res.config.settings",
            views: [[false, "form"]],
        },
        {
            id: 4,
            name: "Other action",
            res_model: "task",
            views: [[false, "list"]],
        },
    ]);
    ResConfigSettings._views.form = /* xml */ `
        <form string="Settings" js_class="base_settings">
            <app string="CRM" name="crm">
                <setting type="header" string="Foo">
                    <field name="foo" title="Foo?."/>
                </setting>
                <button name="4" string="Execute action" type="action"/>
            </app>
        </form>
    `;
    Task._views.list = /* xml */ `<list><field name="display_name"/></list>`;

    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({ foo: true }, { message: "should create a record with foo=true" });
    });

    await mountWithCleanup(WebClient);

    await getService("action").doAction(1);
    expect(".o_field_boolean input").not.toBeChecked({ message: "checkbox should not be checked" });

    await click(".o_field_boolean input");
    await animationFrame();
    expect(".o_field_boolean input").toBeChecked({ message: "checkbox should be checked" });

    expect(".modal-title").toHaveCount(0, {
        message: "should not say that there are unsaved changes",
    });

    await click("button[name='4']");
    await animationFrame();
    expect(".modal").toHaveCount(0, { message: "should not open a warning dialog" });

    expect(".o_list_view").toHaveCount(1, { message: "should be open list view" });
});

test("header without string or field", async () => {
    onRpc("has_group", () => true);
    defineActions([
        {
            id: 1,
            name: "Settings view",
            res_model: "res.config.settings",
            views: [[false, "form"]],
        },
    ]);
    ResConfigSettings._views.form = /* xml */ `
        <form string="Settings" js_class="base_settings">
            <app string="CRM" name="crm">
                <setting type="header">
                    <div><span>Personalize setting</span></div>
                </setting>
                <button name="4" string="Execute action" type="action"/>
            </app>
        </form>
    `;

    await mountWithCleanup(WebClient);

    await getService("action").doAction(1);
    expect(".app_settings_block:not(.d-none) .app_settings_header").toHaveCount(1);
    expect(".app_settings_header label").toHaveCount(0);
});

test("clicking a button with dirty settings -- save", async () => {
    mockService("action", {
        doActionButton(params) {
            expect.step(`action executed ${JSON.stringify(params)}`);
        },
    });
    onRpc(({ method }) => {
        expect.step(method);
    });
    await mountView({
        type: "form",
        arch: /* xml */ `
            <form js_class="base_settings">
                <app string="CRM" name="crm">
                    <field name="foo" />
                    <button type="object" name="mymethod" class="myBtn"/>
                </app>
            </form>
        `,
        resModel: "res.config.settings",
    });
    expect.verifySteps(["get_views", "onchange"]);
    await click(".o_field_boolean input[type='checkbox']");
    await animationFrame();
    await click(".myBtn");
    await animationFrame();
    await click(".modal .btn-primary");
    await animationFrame();
    expect.verifySteps([
        "web_save",
        'action executed {"name":"execute","type":"object","resModel":"res.config.settings","resId":1,"resIds":[1],"context":{"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1]},"buttonContext":{}}',
    ]);
});

test("click on save button which throws an error", async () => {
    expect.errors(1);
    onRpc(({ method }) => {
        expect.step(method);
        if (method === "web_save") {
            throw makeServerError();
        }
    });
    await mountView({
        type: "form",
        arch: /* xml */ `
            <form js_class="base_settings">
                <app string="CRM" name="crm">
                    <field name="foo" />
                </app>
            </form>
        `,
        resModel: "res.config.settings",
    });
    expect.verifySteps(["get_views", "onchange"]);
    expect(".o_form_button_save").toHaveCount(1);
    expect(".o_form_button_save").toHaveProperty("disabled", false);

    await click(".o_field_boolean input[type='checkbox']");
    await animationFrame();
    await click(".o_form_button_save");
    await animationFrame();
    // error are caught asynchronously, so we have to wait for an extra animationFrame, for the error dialog to be mounted
    await animationFrame();
    expect.verifyErrors(["RPC_ERROR"]);
    expect(".o_error_dialog").toHaveCount(1);

    await clickModalButton({ text: "Close" });
    await animationFrame();
    expect(".o_form_button_save").toHaveCount(1);
    expect(".o_form_button_save").toHaveProperty("disabled", false);
    expect.verifySteps(["web_save"]);
});

test("clicking a button with dirty settings -- discard", async () => {
    ResConfigSettings._fields.product_ids = fields.Many2many({
        relation: "product",
        onChange(record) {
            record.product_ids = [
                [
                    4,
                    37,
                    {
                        id: 37,
                        display_name: "xphone",
                    },
                ],
                [
                    4,
                    41,
                    {
                        id: 41,
                        display_name: "xpad",
                    },
                ],
                [
                    1,
                    41,
                    {
                        color: 3,
                    },
                ],
            ];
        },
    });
    ResConfigSettings._fields.bar = fields.Boolean({
        onChange(record) {
            record.bar = true;
        },
    });

    class Product extends models.Model {
        name = fields.Char();
        color = fields.Integer();

        _records = [
            {
                id: 37,
                name: "xphone",
                color: 1,
            },
            {
                id: 41,
                name: "xpad",
                color: 2,
            },
        ];
    }
    defineModels([Product]);

    mockService("action", {
        doActionButton(params) {
            expect.step(`action executed ${JSON.stringify(params)}`);
        },
    });
    onRpc(({ method, args }) => {
        if (method === "web_save") {
            expect.step(method + " - " + JSON.stringify(args[1]));
            return;
        }
        expect.step(method);
    });
    await mountView({
        type: "form",
        arch: /* xml */ `
            <form js_class="base_settings">
                <app string="CRM" name="crm">
                    <field name="product_ids" widget="many2many_tags" options="{ 'color_field': 'color' }"/>
                    <field name="bar" />
                    <field name="foo" />
                    <button type="object" name="mymethod" class="myBtn"/>
                </app>
            </form>
        `,
        resModel: "res.config.settings",
    });
    expect.verifySteps(["get_views", "onchange"]);

    // Initial State:
    // The first checkbox "bar" is checked.
    // Two tags on the many2many : xphone and xpad.
    // The colors are 1 and 3 (the onchange is correctly apply)
    expect(".o_field_boolean[name='bar'] input").toBeChecked();
    expect(queryAllTexts`.o_field_tags .o_tag`).toEqual(["xphone", "xpad"]);
    expect(".o_tag_color_1").toHaveCount(1);
    expect(".o_tag_color_3").toHaveCount(1);
    await click(".o_field_boolean[name='foo'] input[type='checkbox']");
    await animationFrame();
    await click(".myBtn");
    await animationFrame();
    await click(".modal .btn-secondary:eq(1)");
    await animationFrame();
    expect.verifySteps([
        'web_save - {"product_ids":[[4,37],[4,41],[1,41,{"color":3}]],"bar":true,"foo":false}',
        'action executed {"context":{"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1]},"type":"object","name":"mymethod","resModel":"res.config.settings","resId":1,"resIds":[1],"buttonContext":{}}',
    ]);
    // We came back to the same initial state.
    expect(".o_field_boolean[name='bar'] input").toBeChecked();
    expect(queryAllTexts`.o_field_tags .o_tag`).toEqual(["xphone", "xpad"]);
    expect(".o_tag_color_1").toHaveCount(1);
    expect(".o_tag_color_3").toHaveCount(1);
    await click(".o_field_boolean[name='foo'] input[type='checkbox']");
});

test("clicking on a button with noSaveDialog will not show discard warning", async () => {
    onRpc("has_group", () => true);
    expect.assertions(4);

    defineActions([
        {
            id: 1,
            name: "Settings view",
            res_model: "res.config.settings",
            views: [[false, "form"]],
        },
        {
            id: 4,
            name: "Other action",
            res_model: "task",
            views: [[false, "list"]],
        },
    ]);

    ResConfigSettings._views.form = /* xml */ `
        <form string="Settings" js_class="base_settings">
            <app string="CRM" name="crm">
                <block>
                    <setting string="Foo" help="this is foo">
                        <field name="foo"/>
                    </setting>
                </block>
                <button name="4" string="Execute action" type="action" noSaveDialog="true"/>
            </app>
        </form>
    `;
    Task._views.list = /* xml */ `<list><field name="display_name"/></list>`;

    await mountWithCleanup(WebClient);

    await getService("action").doAction(1);
    expect(".o_field_boolean input").not.toBeChecked({ message: "checkbox should not be checked" });

    await click(".o_field_boolean input");
    await animationFrame();
    expect(".o_field_boolean input").toBeChecked({ message: "checkbox should be checked" });

    await click("button[name='4']");
    await animationFrame();
    expect(".modal").toHaveCount(0, { message: "should not open a warning dialog" });

    expect(".o_list_view").toHaveCount(1, { message: "should be open list view" });
});

test("settings view does not display o_not_app settings", async () => {
    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="CRM" name="crm">
                    <block title="CRM">
                        <setting help="this is bar">
                            <field name="bar"/>
                        </setting>
                    </block>
                </app>
                <app notApp="1" string="Other App" name="otherapp">
                    <h2>Other app tab</h2>
                    <block>
                        <setting help="this is bar">
                            <field name="bar"/>
                        </setting>
                    </block>
                </app>
            </form>
        `,
    });

    expect(queryAllTexts(".app_name")).toEqual(["CRM"]);

    expect(queryAllTexts(".settings .o_form_label")).toEqual(["Bar"]);
});

test("settings view shows a message if there are changes", async () => {
    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="Base Setting" name="base-setting">
                    <setting>
                        <field name="bar"/>Make Changes
                    </setting>
                </app>
            </form>
        `,
    });

    expect(".o_field_boolean input").not.toBeChecked({ message: "checkbox should not be checked" });
    expect(".o_control_panel .o_dirty_warning").toHaveCount(0, {
        message: "warning message should not be shown",
    });
    await click(".o_field_boolean input[id=bar_0]");
    await animationFrame();
    expect(".o_field_boolean input").toBeChecked({ message: "checkbox should be checked" });
    expect(".o_control_panel .o_dirty_warning").toHaveCount(1, {
        message: "warning message should be shown",
    });
});

test("settings view shows a message if there are changes even if the save failed", async () => {
    expect.errors(1);
    let alreadySavedOnce = false;
    onRpc(({ method }) => {
        if (method === "web_save" && !alreadySavedOnce) {
            alreadySavedOnce = true;
            //fail on first create
            return Promise.reject({});
        }
    });
    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="Base Setting" name="base-setting">
                    <setting>
                        <field name="bar"/>Make Changes
                    </setting>
                </app>
            </form>
        `,
    });

    await click("input[id=bar_0]");
    await animationFrame();
    expect(".o_control_panel .o_dirty_warning").toHaveCount(1, {
        message: "warning message should be shown",
    });
    await click(".o_control_panel .o_form_button_save");
    await animationFrame();
    expect.verifyErrors(["RPC_ERROR"]);
    expect(".o_control_panel .o_dirty_warning").toHaveCount(1, {
        message: "warning message should be shown",
    });
});

test.tags("desktop");
test("execute action from settings view with several actions in the breadcrumb", async () => {
    onRpc("has_group", () => true);
    // This commit fixes a race condition, that's why we artificially slow down a read rpc
    expect.assertions(4);

    defineActions([
        {
            id: 1,
            name: "First action",
            res_model: "task",
            views: [[1, "list"]],
        },
        {
            id: 2,
            name: "Settings view",
            res_model: "res.config.settings",
            views: [[2, "form"]],
        },
        {
            id: 3,
            name: "Other action",
            res_model: "task",
            views: [[3, "list"]],
        },
    ]);

    Task._views[["list", 1]] = /* xml */ `<list><field name="display_name"/></list>`;
    ResConfigSettings._views[["form", 2]] = /* xml */ `
        <form string="Settings" js_class="base_settings">
            <app string="CRM" name="crm">
                <block title="Title of group">
                    <setting>
                        <button name="3" string="Execute action" type="action"/>
                    </setting>
                </block>
            </app>
        </form>
    `;
    Task._views[["list", 3]] = /* xml */ `<list><field name="display_name"/></list>`;

    let def;
    onRpc("web_save", async () => {
        await def; // slow down reload of settings view
    });

    await mountWithCleanup(WebClient);

    await getService("action").doAction(1);
    expect(".o_breadcrumb").toHaveText("First action");

    await getService("action").doAction(2);
    expect(".o_breadcrumb").toHaveText("First action\nSettings");

    def = new Deferred();
    await click('button[name="3"]');
    await animationFrame();
    expect(".o_breadcrumb").toHaveText("First action\nSettings");

    def.resolve();
    await animationFrame();
    expect(".o_breadcrumb").toHaveText("First action\nSettings\nOther action");
});

test("settings can contain one2many fields", async () => {
    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="Base Setting" name="base-setting">
                    <setting>
                        <field name="tasks">
                            <list><field name="name"/></list>
                            <form><field name="name"/></form>
                        </field>
                    </setting>
                </app>
            </form>
        `,
    });

    await click(".o_field_x2many_list_row_add a");
    await animationFrame();
    await click(".modal-body input");
    await edit("Added Task");
    await animationFrame();
    await click(".modal-footer .btn.o_form_button_save");
    await animationFrame();

    expect("table.o_list_table tr.o_data_row").toHaveText("Added Task", {
        message: "The one2many relation item should have been added",
    });
});

test('call "call_button/execute" when clicking on a button in dirty settings', async () => {
    expect.assertions(4);

    defineActions([
        {
            id: 1,
            name: "Settings view",
            res_model: "res.config.settings",
            views: [[1, "form"]],
        },
        {
            id: 4,
            name: "Other Action",
            res_model: "task",
            views: [[false, "list"]],
        },
    ]);

    ResConfigSettings._views[["form", 1]] = /* xml */ `
        <form string="Settings" js_class="base_settings">
            <app string="CRM" name="crm">
                <block>
                    <setting string="Foo" help="this is foo">
                        <field name="foo"/>
                    </setting>
                    <button name="4" string="Execute action" type="action"/>
                </block>
            </app>
        </form>
    `;

    onRpc("/web/dataset/call_button/*/<string:method>", async (request, { method }) => {
        expect.step(method);
        return true;
    });
    onRpc("web_save", () => {
        expect.step("web_save");
    });

    await mountWithCleanup(WebClient);

    await getService("action").doAction(1);
    expect(".o_field_boolean input").not.toBeChecked({ message: "checkbox should not be checked" });

    await click(".o_field_boolean input");
    await animationFrame();
    expect(".o_field_boolean input").toBeChecked({ message: "checkbox should be checked" });

    await click('button[name="4"]');
    await animationFrame();
    expect(".modal").toHaveCount(1, { message: "should open a warning dialog" });

    await click(".modal-footer .btn-primary");
    await animationFrame();
    expect.verifySteps([
        "web_save", // saveRecord from modal
        "execute", // execute_action
    ]);
});

test("Discard button clean the settings view", async () => {
    onRpc("has_group", () => true);
    expect.assertions(5);

    defineActions([
        {
            id: 1,
            name: "Settings view",
            res_model: "res.config.settings",
            views: [[1, "form"]],
        },
    ]);

    ResConfigSettings._views[["form", 1]] = /* xml */ `
        <form string="Settings" js_class="base_settings">
            <app string="CRM" name="crm">
                <block>
                    <setting string="Foo" help="this is foo">
                        <field name="foo"/>
                    </setting>
                </block>
            </app>
        </form>
    `;

    stepAllNetworkCalls();

    await mountWithCleanup(WebClient);

    await getService("action").doAction(1);
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "/web/action/load",
        "get_views",
        "onchange",
    ]);
    expect(".o_field_boolean input").not.toBeChecked({ message: "checkbox should not be checked" });

    await click(".o_field_boolean input");
    await animationFrame();
    expect(".o_field_boolean input:checked").toHaveCount(1, {
        message: "checkbox should be checked",
    });

    await click(".o_control_panel .o_form_button_cancel");
    await animationFrame();
    expect(".o_field_boolean input").not.toBeChecked({ message: "checkbox should not be checked" });
    expect.verifySteps(["onchange"]);
});

test("Settings Radio widget: show and search", async () => {
    ResConfigSettings._fields.product_id = fields.Many2one({
        relation: "product",
    });
    class Product extends models.Model {
        name = fields.Char();

        _records = [
            {
                id: 37,
                name: "xphone",
            },
            {
                id: 41,
                name: "xpad",
            },
        ];
    }
    defineModels([Product]);

    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="CRM" name="crm">
                    <block>
                        <setting>
                            <label for="product_id"/>
                            <div class="content-group">
                                <div class="mt16">
                                    <field name="product_id" class="o_light_label" widget="radio"/>
                                </div>
                            </div>
                        </setting>
                    </block>
                </app>
            </form>
        `,
    });

    expect(queryAllTexts(".o_radio_item:has(label)")).toEqual(["xphone", "xpad"]);
    await editSearch("xp");
    await runAllTimers();
    expect(".highlighter").toHaveCount(2, { message: "should have 2 options highlighted" });
    expect(queryAllTexts(":has(>.highlighter)")).toEqual(["xphone", "xpad"]);

    await editSearch("xph");
    await runAllTimers();
    expect(".highlighter").toHaveCount(1, { message: "should have only one highlighted" });
    expect(queryAllTexts(":has(>.highlighter)")).toEqual(["xphone"]);
});

test("Settings with createLabelFromField", async () => {
    ResConfigSettings._fields.baz = fields.Selection({
        string: "Zab",
        selection: [
            [1, "treads"],
            [2, "treats"],
        ],
    });

    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="CRM" name="crm">
                    <block title="Title of group Bar">
                        <setting>
                            <label for="baz"/>
                            <field name="baz"/>
                        </setting>
                    </block>
                </app>
            </form>
        `,
    });

    await editSearch("__comp__.props.record");
    await runAllTimers();
    expect(queryAllTexts(".o_settings_container .o_setting_box .o_form_label")).toEqual([]);

    await editSearch("baz");
    await runAllTimers();
    expect(queryAllTexts(".o_settings_container .o_setting_box .o_form_label")).toEqual([]);

    await editSearch("zab");
    await runAllTimers();
    expect(".highlighter").toHaveText("Zab", { message: "Zab word highlighted" });
    expect(queryAllTexts(".o_settings_container .o_setting_box .o_form_label")).toEqual(["Zab"]);
});

test("standalone field labels with string inside a settings page", async () => {
    let compiled = undefined;
    patchWithCleanup(SettingsFormCompiler.prototype, {
        compile() {
            const _compiled = super.compile(...arguments);
            compiled = _compiled;
            return _compiled;
        },
    });

    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form js_class="base_settings">
                <app string="CRM" name="crm">
                    <setting id="setting_id">
                        <label string="My&quot; little &apos;  Label" for="display_name" class="highhopes"/>
                        <field name="display_name" />
                    </setting>
                </app>
            </form>
        `,
    });

    expect("label.highhopes").toHaveText(`My" little ' Label`);
    const expectedCompiled = /* xml */ `
            <SettingsPage slots="{NoContentHelper:__comp__.props.slots.NoContentHelper}" initialTab="__comp__.props.initialApp" t-slot-scope="settings" modules="[{&quot;key&quot;:&quot;crm&quot;,&quot;string&quot;:&quot;CRM&quot;,&quot;imgurl&quot;:&quot;${MOCK_IMAGE}&quot;}]" anchors="[{&quot;app&quot;:&quot;crm&quot;,&quot;settingId&quot;:&quot;setting_id&quot;}]">
                <SettingsApp key="\`crm\`" string="\`CRM\`" imgurl="\`${MOCK_IMAGE}\`" selectedTab="settings.selectedTab">
                    <SearchableSetting info="\`\`" title="\`\`"  help="\`\`" companyDependent="false" documentation="\`\`" record="__comp__.props.record" id="\`setting_id\`" string="\`\`" addLabel="true">
                        <FormLabel id="'display_name_0'" fieldName="'display_name'" record="__comp__.props.record" fieldInfo="__comp__.props.archInfo.fieldNodes['display_name_0']" className="&quot;highhopes&quot;" string="\`My&quot; little '  Label\`"/>
                        <Field id="'display_name_0'" name="'display_name'" record="__comp__.props.record" fieldInfo="__comp__.props.archInfo.fieldNodes['display_name_0']" readonly="__comp__.props.readonly"/>
                    </SearchableSetting>
                </SettingsApp>
            </SettingsPage>`;
    expect(compiled.firstChild).toHaveInnerHTML(expectedCompiled);
});

test("field and artificial label inside a settings page", async () => {
    ResConfigSettings._fields.count = fields.Integer();
    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form js_class="base_settings">
                <app string="CRM" name="crm">
                    <setting id="setting_id">
                        <field name="count" />
                        <span class="o_form_label">
                            items
                        </span>
                    </setting>
                </app>
            </form>
        `,
    });
    expect(".o_field_integer[name=count]").toHaveCount(1);
    expect("span.o_form_label").toHaveInnerHTML(
        `<span searchabletext="\n                            items\n                        ">\n                            items\n                        </span>`
    );
});

test("highlight Element with inner html/fields", async () => {
    let compiled = undefined;
    patchWithCleanup(SettingsFormCompiler.prototype, {
        compile() {
            const _compiled = super.compile(...arguments);
            compiled = _compiled;
            return _compiled;
        },
    });

    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="CRM" name="crm">
                    <block title="Title of group Bar">
                        <setting>
                            <field name="bar"/>
                            <div class="text-muted">this is Baz value: <field name="baz" readonly="1"/> and this is the after text</div>
                        </setting>
                    </block>
                </app>
            </form>
        `,
    });

    expect(".o_setting_right_pane .text-muted").toHaveText(
        "this is Baz value: treads and this is the after text"
    );
    const expectedCompiled = /* xml */ `
            <HighlightText originalText="\`this is Baz value: \`"/>
            <Field id="'baz_0'" name="'baz'" record="__comp__.props.record" fieldInfo="__comp__.props.archInfo.fieldNodes['baz_0']" readonly="__comp__.props.readonly"/>
            <HighlightText originalText="\` and this is the after text\`"/>`;
    expect(queryFirst("SearchableSetting div.text-muted", { root: compiled })).toHaveInnerHTML(
        expectedCompiled
    );
});

test.tags("desktop", "focus required");
test("settings form doesn't autofocus", async () => {
    ResConfigSettings._fields.textField = fields.Char();

    const onFocusIn = (ev) => {
        expect.step(`focusin: ${ev.target.outerHTML}`);
    };

    getFixture().addEventListener("focusin", onFocusIn);

    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="CRM" name="crm">
                    <block title="Title of group Bar">
                        <setting>
                            <field name="textField"/>
                        </setting>
                    </block>
                </app>
            </form>
        `,
    });

    expect("[name='textField'] input").toHaveCount(1);
    expect.verifySteps([
        `focusin: <input type="text" class="o_searchview_input o_input flex-grow-1 w-auto border-0" accesskey="Q" placeholder="Search..." role="searchbox">`,
    ]);
});

test.tags("desktop");
test("settings form keeps scrolling by app", async () => {
    await resize({ height: 200 });

    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="CRM" name="crm">
                    <block title="Title of group Bar">
                        <br /><br /><br /><br /><br /><br /><br /><br /><br /><br /><br />
                        <br /><br /><br /><br /><br /><br /><br /><br /><br /><br /><br />
                        <br /><br /><br /><br /><br /><br /><br /><br /><br /><br /><br />
                        <div id="deepDivCrm" />
                    </block>
                </app>

                <app string="OtherApp" name="otherapp">
                    <block title="Title of group Other">
                        <setting>
                            <br /><br /><br /><br /><br /><br /><br /><br /><br /><br /><br />
                            <br /><br /><br /><br /><br /><br /><br /><br /><br /><br /><br />
                            <br /><br /><br /><br /><br /><br /><br /><br /><br /><br /><br />
                            <div id="deepDivOther" />
                        </setting>
                    </block>
                </app>
            </form>
        `,
    });

    // constrain o_content to have height for its children to be scrollable
    queryFirst(".o_content").style.setProperty("height", "200px");

    const scrollingEl = queryFirst(".settings");
    expect(scrollingEl).toHaveProperty("scrollTop", 0);

    await click(".settings_tab [data-key='otherapp']");
    await animationFrame();
    expect(scrollingEl).toHaveProperty("scrollTop", 0);
    queryFirst("#deepDivOther").scrollIntoView();

    const scrollTop = scrollingEl.scrollTop;
    expect(scrollTop).toBeGreaterThan(0);

    await click(".settings_tab [data-key='crm']");
    await animationFrame();
    expect(scrollingEl).toHaveProperty("scrollTop", 0);

    await click(".settings_tab [data-key='otherapp']");
    await animationFrame();
    expect(scrollingEl).toHaveProperty("scrollTop", scrollTop);
});

test("server actions are called with the correct context", async () => {
    defineActions([
        {
            id: 1,
            name: "Settings view",
            res_model: "res.config.settings",
            views: [[1, "form"]],
        },
        {
            id: 2,
            model_name: "partner",
            name: "Action partner",
            type: "ir.actions.server",
            usage: "ir_actions_server",
        },
    ]);

    ResConfigSettings._views[["form", 1]] = /* xml */ `
        <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
            <app string="CRM" name="crm">
                <button name="2" type="action"/>
            </app>
        </form>
    `;

    onRpc("/web/action/run", async (request) => {
        const {
            params: { context },
        } = await request.json();
        expect.step("/web/action/run");
        const filterContext = pick(context, "active_id", "active_ids", "active_model");
        expect(filterContext).toEqual({
            active_id: 1,
            active_ids: [1],
            active_model: "res.config.settings",
        });
        return new Promise(() => {});
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    await click("button[name='2']");
    await animationFrame();
    expect.verifySteps(["/web/action/run"]);
});

test("BinaryField is correctly rendered in Settings form view", async () => {
    onRpc("/web/content", async (request) => {
        const body = await request.text();
        expect(body).toBeInstanceOf(FormData);
        expect(body.get("field")).toBe("file", {
            message: "we should download the field document",
        });
        expect(body.get("data")).toBe("coucou==\n", {
            message: "we should download the correct data",
        });

        return new Blob([body.get("data")], { type: "text/plain" });
    });

    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="Sale" name="sale">
                    <block title="Title of group Bar">
                        <setting>
                            <field name="task_id" invisible="1"/>
                            <field name="file" filename="file_name" readonly="false"/>
                            <field name="file_name" readonly="false"/>
                        </setting>
                    </block>
                </app>
            </form>
        `,
    });
    expect('.o_field_widget[name="file"] .fa-download').toHaveCount(1, {
        message: "Download button should be display in settings form view",
    });
    expect('.o_field_widget[name="file"].o_field_binary .o_input').toHaveValue("coucou.txt", {
        message: "the binary field should display the file name in the input",
    });
    expect(".o_field_binary .o_clear_file_button").toHaveCount(1, {
        message: "there shoud be a button to clear the file",
    });
    expect(".o_field_char input").toHaveValue("coucou.txt", {
        message: "the filename field should have the file name as value",
    });

    // Testing the download button in the field
    // We must avoid the browser to download the file effectively
    const def = new Deferred();
    const onDownloadClick = (ev) => {
        if (ev.target.tagName === "A" && "download" in ev.target.attributes) {
            ev.preventDefault();
            def.resolve();
        }
    };
    after(on(document, "click", onDownloadClick));
    await click(".fa-download");
    await def;

    await click(".o_field_binary .o_clear_file_button");
    await animationFrame();

    expect(".o_field_binary input").not.toBeVisible({ message: "the input should be hidden" });
    expect(".o_field_binary .o_select_file_button").toHaveCount(1, {
        message: "there should be a button to upload the file",
    });
    expect(".o_field_char input").toHaveValue("", {
        message: "the filename field should be empty since we removed the file",
    });
});

test("Open settings from url, with app anchor", async () => {
    defineActions([
        {
            id: 1,
            name: "Settings view",
            path: "settings",
            res_model: "res.config.settings",
            views: [[false, "form"]],
        },
    ]);
    ResConfigSettings._views.form = /* xml */ `
        <form string="Settings" js_class="base_settings">
            <app string="Not CRM" name="not_crm">
                <block>
                    <setting help="this is bar">
                        <field name="bar"/>
                    </setting>
                </block>
            </app>
            <app string="CRM" name="crm">
                <block>
                    <setting help="this is foo">
                        <field name="foo"/>
                    </setting>
                </block>
            </app>
        </form>
    `;

    redirect("/odoo/settings#crm");
    await mountWithCleanup(WebClient);
    await animationFrame();
    expect(".selected").toHaveAttribute("data-key", "crm", { message: "crm setting selected" });
    expect(queryAllTexts(".settings .o_settings_container .o_form_label")).toEqual(["Foo"]);
});

test("Open settings from url, with setting id anchor", async () => {
    defineActions([
        {
            id: 1,
            name: "Settings view",
            path: "settings",
            res_model: "res.config.settings",
            views: [[false, "form"]],
        },
    ]);
    ResConfigSettings._views.form = /* xml */ `
        <form string="Settings" js_class="base_settings">
            <app string="Not CRM" name="not_crm">
                <block>
                    <setting help="this is bar">
                        <field name="bar"/>
                    </setting>
                </block>
            </app>
            <app string="CRM" name="crm">
                <block>
                    <setting help="this is foo" id="setting_id">
                        <field name="foo"/>
                    </setting>
                </block>
            </app>
        </form>
    `;

    redirect("/odoo/settings#setting_id");
    await mountWebClient();
    expect(".selected").toHaveAttribute("data-key", "crm", { message: "crm setting selected" });
    expect(queryAllTexts(".settings .o_settings_container .o_form_label")).toEqual(["Foo"]);
    expect(".o_setting_highlight").toHaveCount(1);
    expect(queryAllTexts(".settings .o_setting_highlight .o_form_label")).toEqual(["Foo"]);
    await runAllTimers();
    expect(".o_setting_highlight").toHaveCount(0);
});

test.tags("mobile");
test("swipe settings in mobile", async () => {
    mockTouch(true);
    await mountView({
        type: "form",
        resModel: "project",
        arch: `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="CRM" name="crm">
                    <block>
                        <setting help="this is bar">
                            <field name="bar"/>
                        </setting>
                    </block>
                </app>
                <app string="Project" name="project">
                    <block>
                        <setting help="this is foo">
                            <field name="foo"/>
                        </setting>
                    </block>
                </app>
            </form>`,
    });

    await swipeLeft(".settings");
    await runAllTimers();
    await animationFrame();
    expect(".selected").toHaveAttribute("data-key", "project", {
        message: "current setting should be project",
    });

    await swipeRight(".settings");
    await runAllTimers();
    await animationFrame();
    expect(".selected").toHaveAttribute("data-key", "crm", {
        message: "current setting should be crm",
    });
});

test.tags("desktop");
test("swipe settings on larger screen sizes has no effect", async () => {
    mockTouch(true);
    await mountView({
        type: "form",
        resModel: "project",
        arch: `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="CRM" name="crm">
                    <block>
                        <setting help="this is bar">
                            <field name="bar"/>
                        </setting>
                    </block>
                </app>
                <app string="Project" name="project">
                    <block>
                        <setting help="this is foo">
                            <field name="foo"/>
                        </setting>
                    </block>
                </app>
            </form>`,
    });

    await swipeLeft(".settings");
    await runAllTimers();
    await animationFrame();
    expect(".selected").toHaveAttribute("data-key", "crm", {
        message: "current setting should be crm",
    });
});

test("Don't cache settings data", async () => {
    const cache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    defineActions([
        {
            id: 1,
            name: "Settings view",
            path: "settings",
            res_model: "res.config.settings",
            views: [[false, "form"]],
        },
    ]);
    ResConfigSettings._views.form = /* xml */ `
        <form string="Settings" js_class="base_settings">
            <app string="Not CRM" name="not_crm">
                <block>
                    <setting help="this is bar">
                        <field name="bar"/>
                    </setting>
                </block>
            </app>
        </form>
    `;

    await mountWebClient();
    rpc.setCache(cache);
    await getService("action").doAction(1);

    await animationFrame();
    expect(queryAllTexts(".settings .o_settings_container .o_form_label")).toEqual(["Bar"]);

    // The view is cached
    expect(Object.keys(cache.ramCache.ram.get_views)[0].includes("res.config.settings")).toBe(true);
    // The onChange is not cached
    expect(
        Object.keys(cache.ramCache.ram.onchange || {})?.[0]?.includes("res.config.settings")
    ).toBe(undefined);
});

test("settings search is accent-insensitive", async () => {
    await mountView({
        type: "form",
        resModel: "res.config.settings",
        arch: /* xml */ `
            <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                <app string="CRM" name="crm">
                    <block title="Title of group Bâr">
                        <setting help="this is bàr" documentation="/applications/technical/web/settings/this_is_a_test.html">
                            <field name="bar"/>
                            <button name="buttonName" icon="oi-arrow-right" type="action" string="Manage Users" class="btn-link"/>
                        </setting>
                        <setting>
                            <label string="Big BÄZ" for="baz"/>
                            <div class="text-muted">this is a báz</div>
                            <field name="baz"/>
                            <label>label with content</label>
                        </setting>
                    </block>
                </app>
            </form>
        `,
    });
    await editSearch("bar");
    expect(queryAllTexts(".highlighter")).toEqual(["Bâr", "Bar", "bàr"]);
    await editSearch("àz");
    expect(queryAllTexts(".highlighter")).toEqual(["ÄZ", "áz"]);
});
