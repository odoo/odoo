import { animationFrame, expect, test } from "@odoo/hoot";
import { Component, markup, t, useProps, xml } from "@odoo/owl";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";

class Foo extends models.Model {
    foo = fields.Char();
    date = fields.Date();
    _records = [];

    get_help_data(domain) {
        expect.step(`get_help_data ${JSON.stringify(domain)}`);
        return { threshold: 20, show_more: true };
    }
}

class User extends models.Model {
    _name = "res.users";

    has_group() {
        return true;
    }
}

defineModels([Foo, User]);

// The server inlines the help view referenced by the `help_id` attribute of the
// view root node as a <help> child of that node (see `_inline_help_view`).
const HELP = `
    <help>
        <p class="o_help_title">No foo yet</p>
        <a name="action_create_sample" type="object" args="['big']" class="o_help_sample">Load a sample</a>
        <p class="o_help_type" invisible="context.get('foo_type') != 'special'">Special foos</p>
        <t t-out="action_help"/>
    </help>`;

test(`list: help view displayed when there is no record`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/>${HELP}</list>`,
    });
    expect(`.o_view_nocontent .o_help_title`).toHaveText("No foo yet");
    expect(`.o_view_nocontent .o_help_sample`).toHaveCount(1);
    // the buttons of the help aren't considered as list buttons
    expect(`.o_list_renderer thead th:not(.o_list_record_selector)`).toHaveCount(1);
});

test(`help view: action_help renders the action help`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/>${HELP}</list>`,
        noContentHelp: markup("<p class='o_action_help'>From the action</p>"),
    });
    expect(`.o_view_nocontent .o_help_title`).toHaveCount(1);
    expect(`.o_view_nocontent .o_action_help`).toHaveText("From the action");
});

test(`help view: action_help can be invisible`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <help>
                    <p class="o_help_title">No foo yet</p>
                    <t t-out="action_help" invisible="context.get('hide_action_help')"/>
                </help>
            </list>`,
        noContentHelp: markup("<p class='o_action_help'>From the action</p>"),
        context: { hide_action_help: true },
    });
    expect(`.o_view_nocontent .o_help_title`).toHaveCount(1);
    expect(`.o_view_nocontent .o_action_help`).toHaveCount(0);
});

test(`help view: action_help renders a default text without action help`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/>${HELP}</list>`,
    });
    expect(`.o_view_nocontent .o_help_title`).toHaveCount(1);
    expect(`.o_view_nocontent`).toHaveText(/No data to display$/);
});

test(`help view: invisible is evaluated against the action context`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/>${HELP}</list>`,
    });
    expect(`.o_view_nocontent .o_help_type`).toHaveCount(0);
});

test(`help view: invisible is evaluated against the action context (visible)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/>${HELP}</list>`,
        context: { foo_type: "special" },
    });
    expect(`.o_view_nocontent .o_help_type`).toHaveText("Special foos");
});

test(`help view: object buttons are called on an empty recordset, then the view reloads`, async () => {
    onRpc("/web/dataset/call_button/*", async (request) => {
        const { params } = await request.json();
        expect.step(`${params.method} ${JSON.stringify(params.args)}`);
        return false;
    });
    onRpc("web_search_read", () => {
        expect.step("web_search_read");
    });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/>${HELP}</list>`,
    });
    expect.verifySteps(["web_search_read"]);
    await contains(`.o_help_sample`).click();
    expect.verifySteps([`action_create_sample [[],"big"]`, "web_search_read"]);
});

test(`kanban: help view displayed when there is no record`, async () => {
    await mountView({
        resModel: "foo",
        type: "kanban",
        arch: `
            <kanban>
                <templates><t t-name="card"><field name="foo"/></t></templates>
                ${HELP}
            </kanban>`,
    });
    expect(`.o_view_nocontent .o_help_title`).toHaveText("No foo yet");
});

test(`graph: help view displayed over sample data`, async () => {
    await mountView({
        resModel: "foo",
        type: "graph",
        arch: `<graph sample="1"><field name="date"/>${HELP}</graph>`,
    });
    expect(`.o_view_nocontent .o_help_title`).toHaveText("No foo yet");
});

test(`help view: widgets are rendered without record`, async () => {
    class MyWidget extends Component {
        static template = xml`<span class="o_my_widget" t-out="this.props.label"/>`;
        props = useProps({
            readonly: t.boolean().optional(),
            record: t.object().optional(),
            label: t.string(),
        });
    }
    registry.category("view_widgets").add("my_help_widget", {
        component: MyWidget,
        extractProps: ({ attrs }) => ({ label: attrs.label }),
    });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <help><widget name="my_help_widget" label="Hello"/></help>
            </list>`,
    });
    expect(`.o_view_nocontent .o_widget_my_help_widget .o_my_widget`).toHaveText("Hello");
});

test(`help view of the action: used if the view has no help view`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/></list>`,
        noContentHelpArch: `<help><p class="o_action_help_view">From the action</p></help>`,
        noContentHelp: "<p>Action help (html)</p>",
    });
    expect(`.o_view_nocontent .o_action_help_view`).toHaveText("From the action");
});

test(`help view of the action: the view's help view takes precedence`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/>${HELP}</list>`,
        noContentHelpArch: `<help><p class="o_action_help_view">From the action</p></help>`,
    });
    expect(`.o_view_nocontent .o_help_title`).toHaveText("No foo yet");
    expect(`.o_view_nocontent .o_action_help_view`).toHaveCount(0);
});

const HELP_WITH_DATA = `
    <help data_method="get_help_data">
        <p class="o_help_threshold">Threshold: <b t-out="data.threshold"/></p>
        <p class="o_help_more" invisible="not data.get('show_more')">More</p>
        <p class="o_help_less" invisible="data.get('show_more')">Less</p>
    </help>`;

test(`help view: data in a list view`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/>${HELP_WITH_DATA}</list>`,
    });
    expect.verifySteps(["get_help_data []"]);
    expect(`.o_view_nocontent .o_help_threshold`).toHaveText("Threshold: 20");
    expect(`.o_view_nocontent .o_help_more`).toHaveCount(1);
    expect(`.o_view_nocontent .o_help_less`).toHaveCount(0);
});

test(`help view: data in a grouped kanban view`, async () => {
    await mountView({
        resModel: "foo",
        type: "kanban",
        arch: `
            <kanban>
                <templates><t t-name="card"><field name="foo"/></t></templates>
                ${HELP_WITH_DATA}
            </kanban>`,
        groupBy: ["foo"],
    });
    expect.verifySteps(["get_help_data []"]);
    expect(`.o_view_nocontent .o_help_threshold`).toHaveText("Threshold: 20");
});

test(`help view: data in a graph view`, async () => {
    await mountView({
        resModel: "foo",
        type: "graph",
        arch: `<graph sample="1"><field name="date"/>${HELP_WITH_DATA}</graph>`,
    });
    expect.verifySteps(["get_help_data []"]);
    expect(`.o_view_nocontent .o_help_threshold`).toHaveText("Threshold: 20");
});

test(`help view: data are cached, and updated if they changed`, async () => {
    let threshold = 20;
    let def = null;
    onRpc("get_help_data", async () => {
        await def?.promise;
        return { threshold };
    });
    const arch = `<list><field name="foo"/>${HELP_WITH_DATA}</list>`;
    await mountView({ resModel: "foo", type: "list", arch });
    expect(`.o_view_nocontent .o_help_threshold`).toHaveText("Threshold: 20");

    // display the view again: the cached data are displayed directly...
    threshold = 42;
    def = Promise.withResolvers();
    await mountView({ resModel: "foo", type: "list", arch });
    expect(`.o_view_nocontent:last .o_help_threshold`).toHaveText("Threshold: 20");

    // ... and updated when the server returns other ones
    def.resolve();
    await animationFrame();
    expect(`.o_view_nocontent:last .o_help_threshold`).toHaveText("Threshold: 42");
});

test(`help view: data of a previous search are ignored`, async () => {
    let def = null;
    onRpc("get_help_data", async ({ args }) => {
        if (args[0].length) {
            // data of the "My Foos" search are slow to come
            await def.promise;
            return { threshold: 99 };
        }
        return { threshold: 20 };
    });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/>${HELP_WITH_DATA}</list>`,
        searchViewArch: `<search><filter name="my_foos" string="My Foos" domain="[('foo', '=', 'mine')]"/></search>`,
    });
    expect(`.o_view_nocontent .o_help_threshold`).toHaveText("Threshold: 20");

    // search "My Foos", then go back to the initial search before receiving its data
    def = Promise.withResolvers();
    await toggleSearchBarMenu();
    await toggleMenuItem("My Foos");
    await toggleMenuItem("My Foos");
    expect(`.o_view_nocontent .o_help_threshold`).toHaveText("Threshold: 20");

    def.resolve();
    await animationFrame();
    expect(`.o_view_nocontent .o_help_threshold`).toHaveText("Threshold: 20");
});

test(`help view: data reloaded when the search changes`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/>${HELP_WITH_DATA}</list>`,
        searchViewArch: `<search><filter name="my_foos" string="My Foos" domain="[('foo', '=', 'mine')]"/></search>`,
    });
    expect.verifySteps(["get_help_data []"]);

    await toggleSearchBarMenu();
    await toggleMenuItem("My Foos");
    expect.verifySteps([`get_help_data [["foo","=","mine"]]`]);
    expect(`.o_view_nocontent .o_help_threshold`).toHaveText("Threshold: 20");
});

test(`help view: data not requested when there are records`, async () => {
    Foo._records = [{ id: 1, foo: "yop" }];
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/>${HELP_WITH_DATA}</list>`,
    });
    expect(`.o_data_row`).toHaveCount(1);
    expect.verifySteps([]);
});

test(`help view: data not requested without data_method`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/>${HELP}</list>`,
    });
    expect(`.o_view_nocontent .o_help_title`).toHaveCount(1);
    expect.verifySteps([]);
});

test(`help view: data_method of another model (data_model)`, async () => {
    onRpc("get_shared_help_data", ({ model }) => {
        expect.step(`get_shared_help_data on ${model}`);
        return { threshold: 42 };
    });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <field name="foo"/>
                <help data_method="get_shared_help_data" data_model="res.users">
                    <p class="o_help_threshold">Threshold: <b t-out="data.threshold"/></p>
                </help>
            </list>`,
    });
    expect.verifySteps(["get_shared_help_data on res.users"]);
    expect(`.o_view_nocontent .o_help_threshold`).toHaveText("Threshold: 42");
});
