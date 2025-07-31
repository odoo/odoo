import { beforeEach, expect, test } from "@odoo/hoot";
import { hover, queryAllTexts, queryAllValues, queryFirst, runAllTimers } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    editSelectMenu,
    mountView,
    onRpc,
    serverState,
    webModels,
} from "@web/../tests/web_test_helpers";

const { ResCompany, ResGroups, ResPartner, ResUsers } = webModels;

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
            name: "Helpdesk Administrator",
        },
        {
            id: 91,
            name: "Internal user",
        },
        {
            id: 92,
            name: "Portal user",
        },
        {
            id: 93,
            name: "Something related to project",
        },
        {
            id: 94,
            name: "Something related to helpdesk",
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
            group_ids: [1, 11, 91],
            view_group_hierarchy: {
                groups: {
                    1: {
                        id: 1,
                        name: "Access Rights",
                        all_implied_by_ids: [1, 2],
                        all_implied_ids: [],
                        comment: false,
                        disjoint_ids: [],
                        implied_ids: [],
                        privilege_id: 122,
                    },
                    2: {
                        id: 2,
                        name: "Settings",
                        all_implied_by_ids: [2],
                        all_implied_ids: [1, 2, 15],
                        comment: false,
                        disjoint_ids: [],
                        implied_ids: [1, 15],
                        privilege_id: 122,
                    },
                    11: {
                        id: 11,
                        name: "Project User",
                        all_implied_by_ids: [11, 12, 13],
                        all_implied_ids: [11],
                        comment: "Can access Project as a user",
                        disjoint_ids: [],
                        implied_ids: [],
                        privilege_id: 222,
                    },
                    12: {
                        id: 12,
                        name: "Project Manager",
                        all_implied_by_ids: [2, 12, 13, 15],
                        all_implied_ids: [11, 12],
                        comment: "Can access Project as a manager",
                        disjoint_ids: [],
                        implied_ids: [11],
                        privilege_id: 222,
                    },
                    13: {
                        id: 13,
                        name: "Project Administrator",
                        all_implied_by_ids: [13],
                        all_implied_ids: [11, 12, 13, 93],
                        comment: "Can access Project as an admistrator",
                        disjoint_ids: [],
                        implied_ids: [11, 12, 93],
                        privilege_id: 222,
                    },
                    14: {
                        id: 14,
                        name: "Helpdesk User",
                        all_implied_by_ids: [14, 15],
                        all_implied_ids: [11, 14],
                        comment: false,
                        disjoint_ids: [],
                        implied_ids: [11],
                        privilege_id: 223,
                    },
                    15: {
                        id: 15,
                        name: "Helpdesk Administrator",
                        all_implied_by_ids: [15],
                        all_implied_ids: [11, 12, 14, 15, 93, 94],
                        comment: false,
                        disjoint_ids: [],
                        implied_ids: [14, 94],
                        privilege_id: 223,
                    },
                    91: {
                        id: 91,
                        name: "Internal user",
                        all_implied_by_ids: [1, 2, 91],
                        all_implied_ids: [91],
                        comment: false,
                        disjoint_ids: [92],
                        implied_ids: [11],
                        privilege_id: false,
                    },
                    92: {
                        id: 92,
                        name: "Portal user",
                        all_implied_by_ids: [92],
                        all_implied_ids: [92],
                        comment: "Portal members have specific access rights",
                        disjoint_ids: [91],
                        implied_ids: [],
                        privilege_id: false,
                    },
                    93: {
                        id: 93,
                        name: "Something related to project",
                        all_implied_by_ids: [13, 15, 93],
                        all_implied_ids: [93],
                        comment: false,
                        disjoint_ids: [],
                        implied_ids: [],
                        privilege_id: false,
                    },
                    94: {
                        id: 94,
                        name: "Something related to helpdesk",
                        all_implied_by_ids: [15, 94],
                        all_implied_ids: [94],
                        comment: false,
                        disjoint_ids: [],
                        implied_ids: [],
                        privilege_id: false,
                    },
                },
                privileges: {
                    122: {
                        id: 122,
                        name: "Administration",
                        description: false,
                        group_ids: [1, 2],
                        category_id: 121,
                    },
                    222: {
                        id: 222,
                        name: "Project",
                        description: "Project access rights description",
                        group_ids: [11, 12, 13],
                        category_id: 221,
                    },
                    223: {
                        id: 223,
                        name: "Helpdesk",
                        description: "",
                        group_ids: [14, 15],
                        category_id: 221,
                    },
                },
                categories: [
                    {
                        id: 121,
                        name: "Administration (category)",
                        privilege_ids: [122],
                    },
                    {
                        id: 221,
                        name: "Project (category)",
                        privilege_ids: [222, 223],
                    },
                ],
            },
        },
    ];
    serverState.userId = 1;
});

test("simple rendering", async () => {
    await mountView({
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="group_ids" widget="res_user_group_ids"/>
                </sheet>
            </form>`,
        resModel: "res.users",
        resId: 1,
    });

    // 1 group with 2 inner groups
    expect(".o_field_widget[name=group_ids] .o_group").toHaveCount(1);
    expect(".o_field_widget[name=group_ids] .o_group .o_inner_group").toHaveCount(2);

    // first group has one privilege
    expect(
        ".o_field_widget[name=group_ids] .o_inner_group:eq(0) .o_horizontal_separator"
    ).toHaveText("ADMINISTRATION (CATEGORY)");
    expect(".o_field_widget[name=group_ids] .o_inner_group:eq(0) .o_form_label").toHaveCount(1);
    expect(".o_field_widget[name=group_ids] .o_inner_group:eq(0) .o_form_label").toHaveText(
        "Administration"
    );
    expect(".o_field_widget[name=group_ids] .o_inner_group:eq(0) input").toHaveCount(1);
    expect(".o_field_widget[name=group_ids] .o_inner_group:eq(0) input").toHaveValue(
        "Access Rights"
    );

    // second group has 2 privileges
    expect(
        ".o_field_widget[name=group_ids] .o_inner_group:eq(1) .o_horizontal_separator"
    ).toHaveText("PROJECT (CATEGORY)");
    expect(".o_field_widget[name=group_ids] .o_inner_group:eq(1) .o_form_label").toHaveCount(2);
    expect(
        queryAllTexts(".o_field_widget[name=group_ids] .o_inner_group:eq(1) .o_form_label")
    ).toEqual(["Project?", "Helpdesk"]);
    expect(".o_field_widget[name=group_ids] .o_inner_group:nth-child(2) input").toHaveCount(2);
    expect(
        queryAllValues(
            ".o_field_widget[name=group_ids] .o_inner_group:nth-child(2) .o_wrap_input input"
        )
    ).toEqual(["Project User", ""]);

    expect(".o_group_info_button").toHaveCount(0); // not displayed in non debug mode
});

test("simple rendering (debug)", async () => {
    serverState.debug = "1";
    await mountView({
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="group_ids" widget="res_user_group_ids"/>
                </sheet>
            </form>`,
        resModel: "res.users",
        resId: 1,
    });

    // 2 group and 4 inner groups
    expect(".o_field_widget[name=group_ids] .o_group").toHaveCount(2);
    expect(".o_field_widget[name=group_ids] .o_group .o_inner_group").toHaveCount(4);
    expect(".o_group:eq(1) .o_horizontal_separator").toHaveText("EXTRA RIGHTS");
    expect(".o_group:eq(1) .o_inner_group").toHaveCount(2);
    expect(".o_group:eq(1) .o_inner_group:eq(0) input[type=checkbox]").toHaveCount(2);
    expect(".o_group:eq(1) .o_inner_group:eq(0) input[type=checkbox]:checked").toHaveCount(1);
    expect(".o_group:eq(1) .o_inner_group:eq(1) input[type=checkbox]").toHaveCount(2);
    expect(".o_group:eq(1) .o_inner_group:eq(1) input[type=checkbox]:checked").toHaveCount(0);

    expect(".o_group_info_button:not(.invisible)").toHaveCount(3);
});

test("add and remove groups", async () => {
    onRpc("web_save", ({ args }) => {
        expect(args[1].group_ids).toEqual([[6, false, [1, 15, 91]]]);
        expect.step("web_save");
    });

    await mountView({
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="group_ids" widget="res_user_group_ids"/>
                </sheet>
            </form>`,
        resModel: "res.users",
        resId: 1,
    });

    await editSelectMenu(".o_field_widget[name='group_ids'] .o_inner_group:eq(1) input", {
        value: "",
    });
    await editSelectMenu(
        ".o_field_widget[name='group_ids'] .o_inner_group:nth-child(2) .o_wrap_input:last-child input",
        { value: "Helpdesk Administrator" }
    );
    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_save"]);
});

test("editing groups doesn't remove groups (debug)", async () => {
    serverState.debug = "1";
    onRpc("web_save", ({ args }) => {
        expect(args[1].group_ids).toEqual([[6, false, [1, 15, 91]]]);
        expect.step("web_save");
    });

    await mountView({
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="group_ids" widget="res_user_group_ids"/>
                </sheet>
            </form>`,
        resModel: "res.users",
        resId: 1,
    });

    await editSelectMenu(".o_field_widget[name='group_ids'] .o_inner_group:eq(1) input", {
        value: "",
    });
    await editSelectMenu(
        ".o_field_widget[name='group_ids'] .o_inner_group:nth-child(2) .o_wrap_input:last-child input",
        { value: "Helpdesk Administrator" }
    );
    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_save"]);
});

test.tags("desktop");
test(`privilege tooltips`, async () => {
    await mountView({
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="group_ids" widget="res_user_group_ids"/>
                </sheet>
            </form>`,
        resModel: "res.users",
        resId: 1,
    });

    await hover(`.o_form_label sup`);
    await runAllTimers();
    expect(`.o-tooltip .o-tooltip--help`).toHaveText(
        "Project access rights description\n- Project User: Can access Project as a user\n- Project Manager: Can access Project as a manager\n- Project Administrator: Can access Project as an admistrator"
    );
});

test("implied groups rendering", async () => {
    ResUsers._records[0].group_ids = [2, 15];
    await mountView({
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="group_ids" widget="res_user_group_ids"/>
                </sheet>
            </form>`,
        resModel: "res.users",
        resId: 1,
    });

    expect(".o_field_widget[name=group_ids] .o_group .o_inner_group").toHaveCount(2);
    expect(".o_field_widget[name=group_ids] .o_inner_group:eq(1) input").toHaveCount(2);
    expect(queryAllValues(".o_field_widget[name=group_ids] .o_inner_group:eq(1) input")).toEqual([
        "",
        "Helpdesk Administrator",
    ]);
    expect(".o_field_widget[name=group_ids] .o_inner_group:eq(1) input:eq(0)").toHaveAttribute(
        "placeholder",
        "Project Manager"
    );
});

test("implied groups rendering (debug)", async () => {
    serverState.debug = "1";
    ResUsers._records[0].group_ids = [2, 15];
    await mountView({
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="group_ids" widget="res_user_group_ids"/>
                </sheet>
            </form>`,
        resModel: "res.users",
        resId: 1,
    });

    expect(".o_field_widget[name=group_ids] .o_group .o_inner_group").toHaveCount(4);
    expect(".o_field_widget[name=group_ids] .o_inner_group:eq(1) input").toHaveCount(2);
    expect(queryAllValues(".o_field_widget[name=group_ids] .o_inner_group:eq(1) input")).toEqual([
        "",
        "Helpdesk Administrator",
    ]);
    expect(".o_field_widget[name=group_ids] .o_inner_group:eq(1) input:eq(0)").toHaveAttribute(
        "placeholder",
        "Project Manager"
    );

    await contains(".o_inner_group:eq(1) .o_group_info_button:eq(0)").click();
    expect(".o_popover").toHaveCount(1);
    expect(queryAllTexts(".o_popover table td")).toEqual([
        "Project",
        "Project Manager",
        "Implied by",
        "- Administration/Settings\n- Helpdesk/Helpdesk Administrator",
    ]);
    await contains(".o_inner_group:eq(1) .o_group_info_button:eq(1)").click();
    expect(".o_popover").toHaveCount(1);
    expect(queryAllTexts(".o_popover table td")).toEqual([
        "Helpdesk",
        "Helpdesk Administrator",
        "Exclusively implies",
        "- Something related to project\n- Something related to helpdesk",
        "Jointly implies",
        "- Project/Project Manager",
    ]);

    expect(".o_inner_group:eq(2) .o_is_implied input").not.toBeChecked();
    await contains(".o_inner_group:eq(2) .o_group_info_button").click();
    expect(".o_popover").toHaveCount(1);
    expect(queryAllTexts(".o_popover table td")).toEqual([
        "Group",
        "Internal user",
        "Implied by",
        "- Administration/Settings",
    ]);
});

test("implied groups rendering: exclusive (debug)", async () => {
    serverState.debug = "1";
    ResUsers._records[0].group_ids = [15];
    await mountView({
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="group_ids" widget="res_user_group_ids"/>
                </sheet>
            </form>`,
        resModel: "res.users",
        resId: 1,
    });

    expect(".o_field_widget[name=group_ids] .o_group .o_inner_group").toHaveCount(4);
    expect(".o_field_widget[name=group_ids] .o_inner_group:eq(1) input").toHaveCount(2);
    expect(queryAllValues(".o_field_widget[name=group_ids] .o_inner_group:eq(1) input")).toEqual([
        "",
        "Helpdesk Administrator",
    ]);
    expect(".o_field_widget[name=group_ids] .o_inner_group:eq(1) input:eq(0)").toHaveAttribute(
        "placeholder",
        "Project Manager"
    );

    await contains(".o_inner_group:eq(1) .o_group_info_button:eq(0)").click();
    expect(".o_popover").toHaveCount(1);
    expect(queryAllTexts(".o_popover table td")).toEqual([
        "Project",
        "Project Manager",
        "Implied by",
        "- Helpdesk/Helpdesk Administrator",
    ]);
    await contains(".o_inner_group:eq(1) .o_group_info_button:eq(1)").click();
    expect(".o_popover").toHaveCount(1);
    expect(queryAllTexts(".o_popover table td")).toEqual([
        "Helpdesk",
        "Helpdesk Administrator",
        "Exclusively implies",
        "- Something related to project\n- Something related to helpdesk\n- Project/Project Manager",
    ]);
});

test("implied groups: lower level groups no longer available", async () => {
    await mountView({
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="group_ids" widget="res_user_group_ids"/>
                </sheet>
            </form>`,
        resModel: "res.users",
        resId: 1,
    });

    expect(".o_inner_group:eq(1) .o_select_menu").toHaveCount(2);
    await contains(queryFirst(".o_inner_group:eq(1) .o_wrap_input input")).click();
    expect(queryFirst(".o_inner_group:eq(1) .o_wrap_input input")).toHaveValue("Project User");
    expect(".o_select_menu_item").toHaveCount(3);
    expect(".o_inner_group:eq(1) .o_wrap_input:last-child input").toHaveValue("");
    await editSelectMenu(
        ".o_field_widget[name='group_ids'] .o_inner_group:nth-child(2) .o_wrap_input:last-child input",
        { value: "Helpdesk Administrator" }
    );

    await contains(queryFirst(".o_inner_group:eq(1) .o_wrap_input input")).click();
    expect(queryFirst(".o_inner_group:eq(1) .o_wrap_input input")).toHaveValue("");
    expect(queryFirst(".o_inner_group:eq(1) .o_wrap_input input")).toHaveAttribute(
        "placeholder",
        "Project Manager"
    );
    expect(".o_select_menu_item").toHaveCount(2);
    await editSelectMenu(
        ".o_field_widget[name='group_ids'] .o_inner_group:nth-child(2) .o_wrap_input:last-child input",
        { value: "Helpdesk User" }
    );

    expect(queryFirst(".o_inner_group:eq(1) .o_wrap_input input")).toHaveValue("Project User");
    await contains(queryFirst(".o_inner_group:eq(1) .o_wrap_input input")).click();
    expect(".o_select_menu_item").toHaveCount(3);
});

test("implied groups: lower level groups of same privilege still available", async () => {
    ResUsers._records[0].group_ids = [13];
    await mountView({
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="group_ids" widget="res_user_group_ids"/>
                </sheet>
            </form>`,
        resModel: "res.users",
        resId: 1,
    });
    await contains(queryFirst(".o_inner_group:eq(1) .o_wrap_input input")).click();
    expect(".o_select_menu_item").toHaveCount(3);
});

test("do not lose shadowed groups when editing", async () => {
    ResUsers._records[0].group_ids = [11, 15];
    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({
            group_ids: [[6, false, [2, 15, 11]]],
        });
        expect.step("web_save");
    });
    await mountView({
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="group_ids" widget="res_user_group_ids"/>
                </sheet>
            </form>`,
        resModel: "res.users",
        resId: 1,
    });

    await contains(queryFirst(".o_inner_group:eq(1) .o_wrap_input input")).click();
    expect(queryFirst(".o_inner_group:eq(1) .o_wrap_input input")).toHaveValue("");
    expect(queryFirst(".o_inner_group:eq(1) .o_wrap_input input")).toHaveAttribute(
        "placeholder",
        "Project Manager"
    );
    expect(".o_select_menu_item").toHaveCount(2);

    await editSelectMenu(".o_inner_group:eq(0) .o_wrap_input input", { value: "Settings " });
    await contains(queryFirst(".o_inner_group:eq(1) .o_wrap_input input")).click();
    expect(queryFirst(".o_inner_group:eq(1) .o_wrap_input input")).toHaveValue("");
    expect(queryFirst(".o_inner_group:eq(1) .o_wrap_input input")).toHaveAttribute(
        "placeholder",
        "Project Manager"
    );
    expect(".o_select_menu_item").toHaveCount(2);

    await contains(".o_form_button_save").click();
    expect.verifySteps(["web_save"]);
});

test("do not keep shadowed group if higher level group is set", async () => {
    ResUsers._records[0].group_ids = [11, 15];
    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({
            group_ids: [[6, false, [13, 15]]],
        });
        expect.step("web_save");
    });
    await mountView({
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="group_ids" widget="res_user_group_ids"/>
                </sheet>
            </form>`,
        resModel: "res.users",
        resId: 1,
    });

    await contains(queryFirst(".o_inner_group:eq(1) .o_wrap_input input")).click();
    expect(queryFirst(".o_inner_group:eq(1) .o_wrap_input input")).toHaveValue("");
    expect(queryFirst(".o_inner_group:eq(1) .o_wrap_input input")).toHaveAttribute(
        "placeholder",
        "Project Manager"
    );
    expect(".o_select_menu_item").toHaveCount(2);
    await editSelectMenu(".o_inner_group:eq(1) .o_wrap_input input", {
        value: "Project Administrator",
    });
    await contains(".o_form_button_save").click();
    expect.verifySteps(["web_save"]);
});

test("disjoint groups", async () => {
    serverState.debug = "1";
    await mountView({
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="group_ids" widget="res_user_group_ids"/>
                </sheet>
            </form>`,
        resModel: "res.users",
        resId: 1,
    });

    expect(".o_group_info_button.fa-info-circle:not(.invisible)").toHaveCount(3);
    expect(".o_group_info_button.fa-exclamation-triangle:not(.invisible)").toHaveCount(0);
    expect(".o_is_disjoint").toHaveCount(0);

    await contains(".o_inner_group:eq(3) input[type=checkbox]").click();
    expect(".o_group_info_button.fa-info-circle:not(.invisible)").toHaveCount(2);
    expect(".o_group_info_button.fa-exclamation-triangle:not(.invisible)").toHaveCount(2);
    expect(".o_is_disjoint").toHaveCount(2);

    await contains(".o_inner_group:eq(3) .o_group_info_button").click();
    expect(".o_popover").toHaveCount(1);
    expect(queryAllTexts(".o_popover table td")).toEqual([
        "Group",
        "Portal user",
        "Incompatibility",
        "- Internal user",
    ]);
});

test("privileges without category", async () => {
    Object.assign(ResUsers._records[0].view_group_hierarchy.privileges, {
        600: {
            id: 600,
            name: "Other privilege",
            sequence: 10,
            group_ids: [693, 694],
            category_id: false,
        },
    });
    Object.assign(ResUsers._records[0].view_group_hierarchy.groups, {
        693: {
            id: 693,
            name: "Group 1 in Other Privilege",
            all_implied_by_ids: [693],
            all_implied_ids: [693],
            comment: false,
            disjoint_ids: [],
            implied_ids: [],
            privilege_id: 600,
        },
        694: {
            id: 694,
            name: "Group 2 in Other Privilege",
            all_implied_by_ids: [694],
            all_implied_ids: [694],
            comment: false,
            disjoint_ids: [],
            implied_ids: [],
            privilege_id: 600,
        },
    });
    ResGroups._records.push({ id: 693, name: "Group 1 in Other Privilege" });
    ResGroups._records.push({ id: 694, name: "Group 2 in Other Privilege" });

    onRpc("web_save", ({ args }) => {
        expect(args[1].group_ids).toEqual([[6, false, [1, 11, 694, 91]]]);
        expect.step("web_save");
    });
    await mountView({
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="group_ids" widget="res_user_group_ids"/>
                </sheet>
            </form>`,
        resModel: "res.users",
        resId: 1,
    });

    expect(".o_field_widget[name=group_ids] .o_group").toHaveCount(1);
    expect(".o_field_widget[name=group_ids] .o_group .o_inner_group").toHaveCount(3);
    expect(
        ".o_field_widget[name=group_ids] .o_inner_group:eq(2) .o_horizontal_separator"
    ).toHaveText("OTHER");
    expect(".o_field_widget[name=group_ids] .o_inner_group:eq(2) .o_form_label").toHaveText(
        "Other privilege"
    );
    await contains(".o_field_widget[name='group_ids'] .o_inner_group:eq(2) input").click();
    expect(`.o_select_menu_item`).toHaveCount(2);
    await editSelectMenu(".o_field_widget[name='group_ids'] .o_inner_group:eq(2) input", {
        value: "Group 2 in Other Privilege",
    });
    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_save"]);
});
