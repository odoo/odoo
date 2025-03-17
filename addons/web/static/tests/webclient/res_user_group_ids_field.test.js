import { beforeEach, expect, test } from "@odoo/hoot";
import { click, hover, queryAllTexts, runAllTimers, select } from "@odoo/hoot-dom";
import { contains, defineModels, mountView, onRpc } from "@web/../tests/web_test_helpers";
import { ResGroups } from "../_framework/mock_server/mock_models/res_groups";
import { ResUsers } from "../_framework/mock_server/mock_models/res_users";
import { ResCompany } from "../_framework/mock_server/mock_models/res_company";
import { ResPartner } from "../_framework/mock_server/mock_models/res_partner";

defineModels([ResCompany, ResGroups, ResPartner, ResUsers]);

beforeEach(() => {
    ResPartner._records = [{ id: 1, name: "Partner" }];
    ResGroups._records = [
        {
            id: 1,
            name: "Access Rights",
        },
        {
            id: 2,
            name: "Settings",
        },
        {
            id: 11,
            name: "Project User",
        },
        {
            id: 12,
            name: "Project Manager",
        },
        {
            id: 13,
            name: "Project Administrator",
        },
        {
            id: 14,
            name: "Helpdesk User",
        },
        {
            id: 15,
            name: "Helpdesk Administator",
        },
    ];
    ResUsers._records = [
        {
            id: 1,
            company_id: 1,
            company_ids: [1],
            login: "my_user",
            partner_id: 1,
            password: "password",
            group_ids: [1, 11],
            view_group_hierarchy: [
                {
                    id: 121,
                    name: "Administration (section)",
                    categories: [
                        {
                            id: 122,
                            name: "Administration",
                            description: false,
                            groups: [
                                [1, "Access Rights"],
                                [2, "Settings"],
                            ],
                        },
                    ],
                },
                {
                    id: 221,
                    name: "Project (section)",
                    categories: [
                        {
                            id: 222,
                            name: "Project",
                            description: "Project access rights description",
                            groups: [
                                [11, "Project User"],
                                [12, "Project Manager"],
                                [13, "Project Administrator"],
                            ],
                        },
                        {
                            id: 223,
                            name: "Helpdesk",
                            description: "",
                            groups: [
                                [14, "Helpdesk User"],
                                [15, "Helpdesk Administrator"],
                            ],
                        },
                    ],
                },
            ],
        },
    ];
});

test("simple rendering", async () => {
    await mountView({
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="group_ids" nolabel="1" widget="res_user_group_ids"/>
                    </group>
                </sheet>
            </form>`,
        resModel: "res.users",
        resId: 1,
    });

    // 1 group with 2 inner groups
    expect(".o_field_widget[name=group_ids] .o_group").toHaveCount(1);
    expect(".o_field_widget[name=group_ids] .o_group .o_inner_group").toHaveCount(2);
    expect(".o_field_widget[name=group_ids] .o_group .o_inner_group").toHaveCount(2);

    // first group has one category
    expect(
        ".o_field_widget[name=group_ids] .o_inner_group:eq(0) .o_horizontal_separator"
    ).toHaveText("ADMINISTRATION (SECTION)");
    expect(".o_field_widget[name=group_ids] .o_inner_group:eq(0) .o_form_label").toHaveCount(1);
    expect(".o_field_widget[name=group_ids] .o_inner_group:eq(0) .o_form_label").toHaveText(
        "Administration"
    );
    expect(".o_field_widget[name=group_ids] .o_inner_group:eq(0) .o_field_selection").toHaveCount(
        1
    );
    expect(
        ".o_field_widget[name=group_ids] .o_inner_group:eq(0) .o_field_selection select"
    ).toHaveValue("1");

    // second group has 2 categories
    expect(
        ".o_field_widget[name=group_ids] .o_inner_group:eq(1) .o_horizontal_separator"
    ).toHaveText("PROJECT (SECTION)");
    expect(".o_field_widget[name=group_ids] .o_inner_group:eq(1) .o_form_label").toHaveCount(2);
    expect(
        queryAllTexts(".o_field_widget[name=group_ids] .o_inner_group:eq(1) .o_form_label")
    ).toEqual(["Project?", "Helpdesk"]);
    expect(".o_field_widget[name=group_ids] .o_inner_group:eq(1) .o_field_selection").toHaveCount(
        2
    );
    expect(
        ".o_field_widget[name=group_ids] .o_inner_group:eq(1) .o_field_selection:eq(0) select"
    ).toHaveValue("11");
    expect(
        ".o_field_widget[name=group_ids] .o_inner_group:eq(1) .o_field_selection:eq(1) select"
    ).toHaveValue("false");
});

test("add and remove groups", async () => {
    onRpc("web_save", ({ args }) => {
        expect(args[1].group_ids).toEqual([[6, false, [1, 15]]]);
    });

    await mountView({
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="group_ids" nolabel="1" widget="res_user_group_ids"/>
                    </group>
                </sheet>
            </form>`,
        resModel: "res.users",
        resId: 1,
    });

    await click(".o_field_selection select:eq(1)");
    await select("false");
    await click(".o_field_selection select:eq(2)");
    await select("15");
    await contains(`.o_form_button_save`).click();
});

test("editing groups doesn't remove groups that are not in categories", async () => {
    // this group doesn't belong to a category, so it can't be added/removed from the relation
    // with the `res_user_group_ids` widget.
    ResGroups._records.push({
        id: 101,
        name: "Extra Rights",
    });
    ResUsers._records[0].group_ids.push(101);

    onRpc("web_save", ({ args }) => {
        expect(args[1].group_ids).toEqual([[6, false, [101, 1]]]);
    });

    await mountView({
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="group_ids" nolabel="1" widget="res_user_group_ids"/>
                    </group>
                </sheet>
            </form>`,
        resModel: "res.users",
        resId: 1,
    });

    await click(".o_field_selection select:eq(1)");
    await select("false");
    await contains(`.o_form_button_save`).click();
});

test.tags("desktop");
test(`category tooltips`, async () => {
    await mountView({
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="group_ids" nolabel="1" widget="res_user_group_ids"/>
                    </group>
                </sheet>
            </form>`,
        resModel: "res.users",
        resId: 1,
    });

    await hover(`.o_form_label sup`);
    await runAllTimers();
    expect(`.o-tooltip .o-tooltip--help`).toHaveText("Project access rights description");
});
