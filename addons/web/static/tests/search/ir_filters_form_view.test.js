import { beforeEach, expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    getService,
    hideTab,
    MockServer,
    models,
    mountWebClient,
    onRpc,
    serverState,
    webModels,
} from "@web/../tests/web_test_helpers";

const { ResCompany, ResPartner, ResUsers } = webModels;

class Partner extends models.Model {
    name = fields.Char();

    _records = [{ id: 1, name: "First" }];
    _views = { list: `<list><field name="name"/></list>` };
}

class IrFilters extends models.Model {
    name = fields.Char();
    user_ids = fields.Many2many({ relation: "res.users" });

    _records = [
        { id: 1, name: "Shared", user_ids: [serverState.userId, 42] },
        { id: 2, name: "Mine", user_ids: [serverState.userId] },
    ];
    _views = {
        form: `
            <form js_class="ir_filters_form">
                <field name="name"/>
                <field name="user_ids" widget="many2many_tags_avatar"/>
            </form>`,
    };
}

defineModels([Partner, IrFilters, ResCompany, ResPartner, ResUsers]);

function getFilterUserIds(filterId) {
    return MockServer.env["ir.filters"].read([filterId], ["user_ids"])[0].user_ids;
}

async function openFilter(filterId) {
    await getService("action").doAction({
        res_model: "ir.filters",
        type: "ir.actions.act_window",
        res_id: filterId,
        views: [[false, "form"]],
    });
}

beforeEach(async () => {
    ResUsers._records = [...ResUsers._records, { id: 42, name: "Bob" }];
    onRpc("web_save", ({ kwargs }) => {
        expect.step(`web_save, reload: ${!!Object.keys(kwargs.specification).length}`);
    });
    await mountWebClient();
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "list"]],
    });
});

test("leaving a shared filter saves without reloading and goes back", async () => {
    await openFilter(1);
    await contains(".o_field_many2many_tags_avatar .o_tag:eq(0) .o_delete", {
        visible: false,
    }).click();
    await contains(".o_form_button_save").click();
    expect(".o_list_view").toHaveCount(1);
    expect.verifySteps(["web_save, reload: false"]);
    expect(getFilterUserIds(1)).toEqual([42]);
});

test("leaving a shared filter through the breadcrumbs goes back once", async () => {
    await openFilter(1);
    await contains(".o_field_many2many_tags_avatar .o_tag:eq(0) .o_delete", {
        visible: false,
    }).click();
    await contains(".o_breadcrumb .o_back_button").click();
    expect(".o_list_view").toHaveCount(1);
    expect.verifySteps(["web_save, reload: false"]);
    expect(getFilterUserIds(1)).toEqual([42]);
});

test("leaving a shared filter is not autosaved when the tab is hidden", async () => {
    await openFilter(1);
    await contains(".o_field_many2many_tags_avatar .o_tag:eq(0) .o_delete", {
        visible: false,
    }).click();
    expect(".o_field_many2many_tags_avatar .o_tag").toHaveCount(1);
    await hideTab();
    expect(".o_form_view").toHaveCount(1);
    expect.verifySteps([]);
    expect(getFilterUserIds(1)).toEqual([serverState.userId, 42]);
});

test("removing another user from a shared filter stays on the form", async () => {
    await openFilter(1);
    await contains(".o_field_many2many_tags_avatar .o_tag:eq(1) .o_delete", {
        visible: false,
    }).click();
    await contains(".o_form_button_save").click();
    expect(".o_form_view").toHaveCount(1);
    expect.verifySteps(["web_save, reload: true"]);
    expect(getFilterUserIds(1)).toEqual([serverState.userId]);
});

test("removing the only user of a filter makes it global and stays on the form", async () => {
    await openFilter(2);
    await contains(".o_field_many2many_tags_avatar .o_tag:eq(0) .o_delete", {
        visible: false,
    }).click();
    await contains(".o_form_button_save").click();
    expect(".o_form_view").toHaveCount(1);
    expect.verifySteps(["web_save, reload: true"]);
    expect(getFilterUserIds(2)).toEqual([]);
});
