import { expect, test, beforeEach, describe } from "@odoo/hoot";
import { queryFirst, queryAll, click } from "@odoo/hoot-dom";
import { animationFrame, mockDate } from "@odoo/hoot-mock";

import { fields, onRpc, mountView, getKwArgs } from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";

import { definePlanningModels, planningModels } from "./planning_mock_models";

describe.current.tags("desktop");

/* Main Goals of these tests:
    - Tests the change made in planning to avatar card preview for resource:
        - Roles appear as tags on the card
        - Card should be displayed for material resources with at least 2 roles
    - Test the integration of the card in the Gantt view
*/

/* 1. Create data
   4 type of records tested:
    - Planning slot linked to a material resource with only one role
        - clicking the icon should not open any popover
    - Planning slot linked to a material resource with two roles
        - clicking the icon should open a card popover with resource name and roles
    - Planning slot linked to a human resource not linked to a user
        - a card popover should open including the roles of the employee
    - Planning slot linked to a human resource linked to a user
        - a card popover should open including the roles of the employee
*/

class PlanningSlot extends planningModels.PlanningSlot {
    resource_roles = fields.One2many({ relation: "planning.role" });

    _records = [
        {
            display_name: "Planning Slot tester 1",
            resource_id: 1,
            resource_type: "material",
            resource_roles: [1],
            user_id: false,
            start_datetime: "2023-11-09 00:00:00",
            end_datetime: "2023-11-09 22:00:00",
        },
        {
            display_name: "Planning slot integration tester",
            resource_id: 2,
            resource_type: "material",
            resource_roles: [1, 2],
            user_id: false,
            start_datetime: "2023-11-09 00:00:00",
            end_datetime: "2023-11-09 22:00:00",
        },
        {
            display_name: "Planning slot Marie",
            resource_id: 3,
            resource_type: "user",
            resource_roles: [1],
            user_id: false,
            start_datetime: "2023-11-09 00:00:00",
            end_datetime: "2023-11-09 22:00:00",
        },
        {
            display_name: "Planning Slot Pierre",
            resource_id: 4,
            resource_type: "user",
            resource_roles: [2],
            user_id: 1,
            start_datetime: "2023-11-09 00:00:00",
            end_datetime: "2023-11-09 22:00:00",
        },
    ];
}

class PlanningRole extends planningModels.PlanningRole {
    _records = [
        {
            id: 1,
            name: "Tester",
            color: 1,
        },
        {
            id: 2,
            name: "It Specialist",
            color: 2,
        },
    ];
}

class ResourceResource extends planningModels.ResourceResource {
    _records = [
        {
            id: 1,
            name: "Continuity testing computer",
            resource_type: "material",
            role_ids: [1],
        },
        {
            id: 2,
            name: "Integration testing computer",
            resource_type: "material",
            role_ids: [1, 2],
        },
        {
            id: 3,
            name: "Marie",
            resource_type: "user",
            role_ids: [1],
        },
        {
            id: 4,
            name: "Pierre",
            resource_type: "user",
            role_ids: [2],
            user_id: 1,
            im_status: "online",
        },
    ];

    get_avatar_card_data(ids, fields) {
        const kwargs = getKwArgs(arguments, "ids", "fields");
        return this.read(kwargs.ids, kwargs.fields);
    }
}

class HrEmployee extends planningModels.HrEmployee {
    _records = [
        {
            id: 1,
            name: "Marie",
            resource_id: 3,
        },
        {
            id: 2,
            name: "Pierre",
            resource_id: 4,
            user_id: 1,
            user_partner_id: 1,
        },
    ];
}

// Imitating the server behavior by creating an hr.employee.public record with the same data and same id
class HrEmployeePublic extends planningModels.HrEmployeePublic {
    _records = [
        {
            id: 1,
            name: "Marie",
        },
        {
            id: 2,
            name: "Pierre",
            user_id: 1,
            user_partner_id: 1,
        },
    ];
}

planningModels.PlanningSlot = PlanningSlot;
planningModels.PlanningRole = PlanningRole;
planningModels.ResourceResource = ResourceResource;
planningModels.HrEmployee = HrEmployee;
planningModels.HrEmployeePublic = HrEmployeePublic;

definePlanningModels();

beforeEach(() => {
    mailModels.ResUsers._records.push({
        id: 1,
        name: "Pierre",
        partner_id: 1,
    });
});

test("many2one_avatar_resource widget in kanban view", async () => {
    await mountView({
        resModel: "planning.slot",
        type: "kanban",
        arch: `<kanban>
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                        <field name="resource_id" widget="many2one_avatar_resource"/>
                    </t>
                </templates>
            </kanban>
        `,
    });

    expect(".o_m2o_avatar").toHaveCount(4);

    // fa-wrench should be displayed for first two planning slots
    expect(".o_m2o_avatar > span.o_material_resource > i.fa-wrench").toHaveCount(2, {
        message:
            "material icon should be displayed for the first two gantt rows (material resources)",
    });

    // Third and fourth slots should display employee avatar
    expect(".o_field_many2one_avatar_resource img").toHaveCount(2);
    expect(
        queryFirst(
            ".o_kanban_record:nth-of-type(3) .o_field_many2one_avatar_resource img"
        ).getAttribute("data-src")
    ).toBe("/web/image/resource.resource/3/avatar_128", {
        message: "There should be the ID 3 in the URL as it is the one of resource 'Marie'",
    });
    expect(
        queryFirst(
            ".o_kanban_record:nth-of-type(4) .o_field_many2one_avatar_resource img"
        ).getAttribute("data-src")
    ).toBe("/web/image/resource.resource/4/avatar_128", {
        message: "There should be the ID 4 in the URL as it is the one of resource 'Pierre'",
    });

    // 1. Clicking on material resource's icon with only one role
    await click(".o_kanban_record:nth-of-type(1) .o_m2o_avatar");
    await animationFrame();
    expect(".o_avatar_card").toHaveCount(0);

    // 2. Clicking on material resource's icon with two roles
    await click(".o_kanban_record:nth-of-type(2) .o_m2o_avatar");
    await animationFrame();
    expect(".o_avatar_card").toHaveCount(1);
    expect(".o_avatar_card .o_avatar > img").toHaveCount(0, {
        message: "There should not be any avatar for material resource",
    });
    expect(".o_avatar_card_buttons button").toHaveCount(0);
    expect(".o_avatar_card .o_resource_roles_tags > .o_tag").toHaveCount(2, {
        message: "Roles should be listed in the card",
    });

    // 3. Clicking on human resource's avatar with no user associated
    await click(".o_kanban_record:nth-of-type(3) .o_m2o_avatar");
    await animationFrame();
    expect(".o_card_user_infos span:first").toHaveText("Marie");

    // 4. Clicking on human resource's avatar with one user associated
    await click(".o_kanban_record:nth-of-type(4) .o_m2o_avatar");
    await animationFrame();
    expect(".o_card_user_infos span:first").toHaveText("Pierre");
});

test("Employee avatar in Gantt view", async () => {
    mockDate("2023-11-08 8:00:00", 0);
    onRpc("gantt_resource_work_interval", () => {
        return [
            {
                1: [
                    ["2022-10-10 06:00:00", "2022-10-10 10:00:00"], //Monday    4h
                    ["2022-10-11 06:00:00", "2022-10-11 10:00:00"], //Tuesday   5h
                    ["2022-10-11 11:00:00", "2022-10-11 12:00:00"],
                    ["2022-10-12 06:00:00", "2022-10-12 10:00:00"], //Wednesday 6h
                    ["2022-10-12 11:00:00", "2022-10-12 13:00:00"],
                    ["2022-10-13 06:00:00", "2022-10-13 10:00:00"], //Thursday  7h
                    ["2022-10-13 11:00:00", "2022-10-13 14:00:00"],
                    ["2022-10-14 06:00:00", "2022-10-14 10:00:00"], //Friday    8h
                    ["2022-10-14 11:00:00", "2022-10-14 15:00:00"],
                ],
            },
        ];
    });
    onRpc("get_gantt_data", ({ kwargs, parent }) => {
        const result = parent();
        expect(kwargs.progress_bar_fields).toEqual(["resource_id"]);
        result.progress_bars.resource_id = {
            1: {
                value: 100,
                max_value: 100,
                is_material_resource: true,
                resource_color: 1,
                display_popover_material_resource: false,
                employee_id: false,
            },
            2: {
                value: 100,
                max_value: 100,
                is_material_resource: true,
                resource_color: 1,
                display_popover_material_resource: true, // Testing this full behavior would require a tour
                employee_id: false,
            },
            3: {
                value: 100,
                max_value: 100,
                is_material_resource: false,
                resource_color: false,
                display_popover_material_resource: false,
                employee_id: 1,
            },
            4: {
                value: 100,
                max_value: 100,
                is_material_resource: false,
                resource_color: false,
                display_popover_material_resource: false,
                employee_id: 2,
            },
        };
        return result;
    });
    await mountView({
        resModel: "planning.slot",
        type: "gantt",
        arch: `<gantt js_class="planning_gantt" date_start="start_datetime" date_stop="end_datetime" progress_bar="resource_id"/>`,
        groupBy: ["resource_id"],
    });
    expect(".o_gantt_row_title .o_avatar").toHaveCount(4);
    expect(".o_avatar .o_material_resource .fa-wrench").toHaveCount(2, {
        message:
            "material icon should be displayed for the first two gantt rows (material resources)",
    });
    expect(".o_gantt_row_title .o_avatar img").toHaveCount(2, {
        message: "avatar should be displayed for the third and fourth gantt rows (human resources)",
    });
    expect(queryAll(".o_gantt_row_title .o_avatar img")[1].getAttribute("data-src")).toBe(
        "/web/image/resource.resource/4/avatar_128",
        {
            message:
                "avatar of the employee associated to the human resource should be displayed on fourth row",
        }
    );

    // 1. Clicking on material resource's icon with only one role
    await click(".o_avatar .o_material_resource .fa-wrench");
    await animationFrame();
    expect(".o_avatar_card").toHaveCount(0);

    // 2. Clicking on material resource's icon with two roles
    await click(queryAll(".o_avatar .o_material_resource .fa-wrench")[1]);
    await animationFrame();
    expect(".o_avatar_card").toHaveCount(1);
    expect(".o_avatar_card .o_avatar > img").toHaveCount(0, {
        message: "There should not be any avatar for material resource",
    });
    expect(".o_avatar_card_buttons button").toHaveCount(0);
    expect(".o_avatar_card .o_resource_roles_tags > .o_tag").toHaveCount(2, {
        message: "Roles should be listed in the card",
    });

    // 3. Clicking on human resource's avatar with no user associated
    await click(".o_gantt_row_title .o_avatar img");
    await animationFrame();
    expect(".o_card_user_infos span:first").toHaveText("Marie");
    expect(".o_avatar_card").toHaveCount(1, {
        message: "Only one popover resource card should be opened at a time",
    });

    // 4. Clicking on human resource's avatar with one user associated
    await click(queryAll(".o_gantt_row_title .o_avatar img")[1]);
    await animationFrame();
    expect(".o_card_user_infos span:first").toHaveText("Pierre");
    expect(".o_avatar_card").toHaveCount(1, {
        message: "Only one popover resource card should be opened at a time",
    });
});
