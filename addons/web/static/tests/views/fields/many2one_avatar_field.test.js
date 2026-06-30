import { expect, test } from "@odoo/hoot";
import { queryAll, queryAllTexts } from "@odoo/hoot-dom";
import { runAllTimers } from "@odoo/hoot-mock";

import {
    clickFieldDropdown,
    clickFieldDropdownItem,
    clickSave,
    contains,
    defineModels,
    fields,
    models,
    mountView,
    patchWithCleanup,
    stepAllNetworkCalls,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";

class Partner extends models.Model {
    int_field = fields.Integer();
    user_id = fields.Many2one({ string: "Users", relation: "res.users" });
    _records = [
        { id: 1, user_id: 1 },
        { id: 2, user_id: 2 },
        { id: 3, user_id: 1 },
        { id: 4, user_id: false },
    ];
}

class Users extends models.Model {
    _name = "res.users";
    name = fields.Char();
    partner_ids = fields.One2many({ relation: "partner", relation_field: "user_id" });

    has_group() {
        return true;
    }

    _records = [
        {
            id: 1,
            name: "Aline",
        },
        {
            id: 2,
            name: "Christine",
        },
    ];
}

defineModels([Partner, Users]);

test.tags("desktop");
test("basic form view flow", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="user_id" widget="many2one_avatar"/>
            </form>`,
    });

    expect(".o_field_widget[name=user_id] input").toHaveValue("Aline");
    expect('.o_m2o_avatar > img[data-src="/web/image/res.users/1/avatar_128"]').toHaveCount(1);
    expect(".o_field_many2one_avatar > div").toHaveCount(1);

    expect(".o_input_dropdown").toHaveCount(1);
    expect(".o_input_dropdown input").toHaveValue("Aline");
    expect(".o_external_button").toHaveCount(1);
    expect('.o_m2o_avatar > img[data-src="/web/image/res.users/1/avatar_128"]').toHaveCount(1);

    await clickFieldDropdown("user_id");
    expect(".o_field_many2one_selection .o_avatar_many2x_autocomplete").toHaveCount(2);
    await clickFieldDropdownItem("user_id", "Christine");

    expect('.o_m2o_avatar > img[data-src="/web/image/res.users/2/avatar_128"]').toHaveCount(1);
    await clickSave();

    expect(".o_field_widget[name=user_id] input").toHaveValue("Christine");
    expect('.o_m2o_avatar > img[data-src="/web/image/res.users/2/avatar_128"]').toHaveCount(1);

    await contains('.o_field_widget[name="user_id"] input').clear({ confirm: "blur" });

    expect(".o_m2o_avatar > img").toHaveCount(0);
    expect(".o_m2o_avatar > .o_m2o_avatar_empty").toHaveCount(1);
    await clickSave();

    expect(".o_m2o_avatar > img").toHaveCount(0);
    expect(".o_m2o_avatar > .o_m2o_avatar_empty").toHaveCount(1);
});

test("onchange in form view flow", async () => {
    Partner._fields.int_field = fields.Integer({
        onChange: (obj) => {
            if (obj.int_field === 1) {
                obj.user_id = [2, "Christine"];
            } else if (obj.int_field === 2) {
                obj.user_id = false;
            } else {
                obj.user_id = [1, "Aline"]; // default value
            }
        },
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="int_field"/>
                <field name="user_id" widget="many2one_avatar" readonly="1"/>
            </form>`,
    });

    expect(".o_field_widget[name=user_id]").toHaveText("Aline");
    expect('.o_m2o_avatar > img[data-src="/web/image/res.users/1/avatar_128"]').toHaveCount(1);

    await contains("div[name=int_field] input").edit(1);

    expect(".o_field_widget[name=user_id]").toHaveText("Christine");
    expect('.o_m2o_avatar > img[data-src="/web/image/res.users/2/avatar_128"]').toHaveCount(1);

    await contains("div[name=int_field] input").edit(2);

    expect(".o_field_widget[name=user_id]").toHaveText("");
    expect(".o_m2o_avatar > img").toHaveCount(0);
});

test("basic list view flow", async () => {
    await mountView({
        type: "list",
        resModel: "partner",
        arch: '<list><field name="user_id" widget="many2one_avatar"/></list>',
    });

    expect(queryAllTexts(".o_data_cell[name='user_id']")).toEqual([
        "Aline",
        "Christine",
        "Aline",
        "",
    ]);
    const imgs = queryAll(".o_m2o_avatar > img");
    expect(imgs[0]).toHaveAttribute("data-src", "/web/image/res.users/1/avatar_128");
    expect(imgs[1]).toHaveAttribute("data-src", "/web/image/res.users/2/avatar_128");
    expect(imgs[2]).toHaveAttribute("data-src", "/web/image/res.users/1/avatar_128");
});

test("basic flow in editable list view", async () => {
    await mountView({
        type: "list",
        resModel: "partner",
        arch: '<list editable="top"><field name="user_id" widget="many2one_avatar"/></list>',
    });

    expect(queryAllTexts(".o_data_cell[name='user_id']")).toEqual([
        "Aline",
        "Christine",
        "Aline",
        "",
    ]);

    const imgs = queryAll(".o_m2o_avatar > img");
    expect(imgs[0]).toHaveAttribute("data-src", "/web/image/res.users/1/avatar_128");
    expect(imgs[1]).toHaveAttribute("data-src", "/web/image/res.users/2/avatar_128");
    expect(imgs[2]).toHaveAttribute("data-src", "/web/image/res.users/1/avatar_128");

    await contains(".o_data_row .o_data_cell:eq(0)").click();

    expect(".o_m2o_avatar > img:eq(0)").toHaveAttribute(
        "data-src",
        "/web/image/res.users/1/avatar_128"
    );
});

test("Many2OneAvatar with placeholder", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="user_id" widget="many2one_avatar" placeholder="Placeholder"/></form>',
    });

    expect(".o_field_widget[name='user_id'] input").toHaveAttribute("placeholder", "Placeholder");
});

test.tags("desktop");
test("click on many2one_avatar in a list view (multi_edit='1')", async () => {
    const listView = registry.category("views").get("list");
    patchWithCleanup(listView.Controller.prototype, {
        openRecord() {
            expect.step("openRecord");
        },
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list multi_edit="1">
                <field name="user_id" widget="many2one_avatar"/>
            </list>`,
    });

    await contains(".o_data_row:eq(0) .o_list_record_selector input").click();
    await contains(".o_data_row .o_data_cell [name='user_id']").click();
    expect(".o_data_row:eq(0)").toHaveClass("o_selected_row");

    expect.verifySteps([]);
});

test("click on many2one_avatar in an editable list view", async () => {
    const listView = registry.category("views").get("list");
    patchWithCleanup(listView.Controller.prototype, {
        openRecord() {
            expect.step("openRecord");
        },
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list>
                <field name="user_id" widget="many2one_avatar"/>
            </list>`,
    });

    await contains(".o_data_row .o_data_cell [name='user_id']").click();
    expect(".o_selected_row").toHaveCount(0);

    expect.verifySteps(["openRecord"]);
});

test.tags("desktop");
test("click on many2one_avatar in an editable list view (editable top)", async () => {
    const listView = registry.category("views").get("list");
    patchWithCleanup(listView.Controller.prototype, {
        openRecord() {
            expect.step("openRecord");
        },
    });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list editable="top">
                <field name="user_id" widget="many2one_avatar"/>
            </list>`,
    });

    await contains(".o_data_row .o_data_cell [name='user_id']").click();
    expect(".o_data_row:eq(0)").toHaveClass("o_selected_row");

    expect.verifySteps([]);
});

test("readonly many2one_avatar in form view should contain a link", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form><field name="user_id" widget="many2one_avatar" readonly="1"/></form>`,
    });

    expect("[name='user_id'] a").toHaveCount(1);
});

test("readonly many2one_avatar in list view should not contain a link", async () => {
    await mountView({
        type: "list",
        resModel: "partner",
        arch: `<list><field name="user_id" widget="many2one_avatar"/></list>`,
    });

    expect("[name='user_id'] a").toHaveCount(0);
});

test("readonly many2one_avatar in form view with no_open set to true", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form><field name="user_id" widget="many2one_avatar" readonly="1" options="{'no_open': 1}"/></form>`,
    });

    expect("[name='user_id'] a").toHaveCount(0);
});

test("readonly many2one_avatar in list view with no_open set to false", async () => {
    await mountView({
        type: "list",
        resModel: "partner",
        arch: `<list><field name="user_id" widget="many2one_avatar" options="{'no_open': 0}"/></list>`,
    });

    expect("[name='user_id'] a").toHaveCount(3);
});

test.tags("desktop");
test("cancelling create dialog should clear value in the field", async () => {
    Users._views = {
        form: `
            <form>
                <field name="name" />
            </form>`,
    };

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list editable="top">
                <field name="user_id" widget="many2one_avatar"/>
            </list>`,
    });

    await contains(".o_data_cell:eq(0)").click();
    await contains(".o_field_widget[name=user_id] input").edit("yy", { confirm: false });
    await runAllTimers();
    await clickFieldDropdownItem("user_id", "Create and edit...");

    await contains(".o_form_button_cancel").click();
    expect(".o_field_widget[name=user_id] input").toHaveValue("");
    expect(".o_field_widget[name=user_id] span.o_m2o_avatar_empty").toHaveCount(1);
});

test.tags("desktop");
test("widget many2one_avatar in kanban view (load more dialog)", async () => {
    expect.assertions(1);

    for (let id = 3; id <= 12; id++) {
        Users._records.push({
            id,
            display_name: `record ${id}`,
        });
    }

    Users._views = {
        list: '<list><field name="display_name"/></list>',
    };
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <footer>
                            <field name="user_id" widget="many2one_avatar"/>
                        </footer>
                    </t>
                </templates>
            </kanban>`,
    });

    // open popover
    await contains(
        ".o_kanban_record:nth-child(4) .o_field_many2one_avatar .o_m2o_avatar > a.o_quick_assign"
    ).click();

    // load more
    await contains(".o-overlay-container .o_m2o_dropdown_option_search_more").click();
    await contains(".o_dialog .o_list_table .o_data_row .o_data_cell").click();
    expect(
        ".o_kanban_record:nth-child(4) .o_field_many2one_avatar .o_m2o_avatar > img"
    ).toHaveAttribute("data-src", "/web/image/res.users/1/avatar_128");
});

test("widget many2one_avatar in kanban view", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <footer>
                            <field name="user_id" widget="many2one_avatar"/>
                        </footer>
                    </t>
                </templates>
            </kanban>`,
    });
    stepAllNetworkCalls();

    expect(
        ".o_kanban_record:nth-child(1) .o_field_many2one_avatar .o_m2o_avatar > img"
    ).toHaveAttribute("data-src", "/web/image/res.users/1/avatar_128");
    expect(
        ".o_kanban_record:nth-child(4) .o_field_many2one_avatar .o_m2o_avatar > .o_quick_assign"
    ).toHaveCount(1);
    // open popover
    await contains(
        ".o_kanban_record:nth-child(4) .o_field_many2one_avatar .o_m2o_avatar > .o_quick_assign"
    ).click();
    expect(".o-overlay-container input").toBeFocused();
    expect.verifySteps(["web_name_search"]);
    // select first input
    await contains(".o-overlay-container .o-autocomplete--dropdown-item").click();
    expect.verifySteps(["web_save"]);
    expect(
        ".o_kanban_record:nth-child(4) .o_field_many2one_avatar .o_m2o_avatar > img"
    ).toHaveAttribute("data-src", "/web/image/res.users/1/avatar_128");
    expect(
        ".o_kanban_record:nth-child(4) .o_field_many2one_avatar .o_m2o_avatar > .o_quick_assign"
    ).toHaveCount(0);
});

test("widget many2one_avatar in kanban view without access rights", async () => {
    expect.assertions(2);
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban edit="0" create="0">
                <templates>
                    <t t-name="card">
                        <footer>
                            <field name="user_id" widget="many2one_avatar"/>
                        </footer>
                    </t>
                </templates>
            </kanban>`,
    });
    expect(
        ".o_kanban_record:nth-child(1) .o_field_many2one_avatar .o_m2o_avatar > img"
    ).toHaveAttribute("data-src", "/web/image/res.users/1/avatar_128");
    expect(
        ".o_kanban_record:nth-child(4) .o_field_many2one_avatar .o_m2o_avatar > .o_quick_assign"
    ).toHaveCount(0);
});
