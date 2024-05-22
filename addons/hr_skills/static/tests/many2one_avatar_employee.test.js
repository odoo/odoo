import {
    click,
    contains,
    openKanbanView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryAttribute } from "@odoo/hoot-dom";
import { defineHrSkillModels } from "@hr_skills/../tests/hr_skills_test_helpers";

describe.current.tags("desktop");
defineHrSkillModels();

beforeEach(async () => {
    const pyEnv = await startServer();
    this.data = {};

    // Skills
    [this.data.skillJavaId, this.data.skillTigrinya] = pyEnv["hr.skill"].create([
        {
            name: "Java",
        },
        {
            name: "Tigrinya",
        },
    ]);

    // User
    this.data.partnerPierreId = pyEnv["res.partner"].create({
        name: "Pierre",
    });
    this.data.userPierreId = pyEnv["res.users"].create({
        name: "Pierre",
        partner_id: this.data.partnerPierreId,
    });

    // Employees
    this.data.employeePierreId = pyEnv["hr.employee"].create({
        name: "Pierre",
        user_id: this.data.userPierreId,
        user_partner_id: this.data.partnerPierreId,
    });

    // Employee skills
    [this.data.employeeSkill1Id, this.data.employeeSkill2Id] = pyEnv["hr.employee.skill"].create([
        {
            employee_id: this.data.employeePierreId,
            skill_id: this.data.skillJavaId,
        },
        {
            employee_id: this.data.employeePierreId,
            skill_id: this.data.skillTigrinyaId,
        },
    ]);

    // Public employee
    // Imitating the server behavior by creating an hr.employee.public record with the same data and same id
    pyEnv["hr.employee.public"].create({
        name: "Pierre",
        employee_skill_ids: [this.data.employeeSkill1Id, this.data.employeeSkill2Id],
    });

    // Fake record
    this.data.recordPierreId = pyEnv["m2o.avatar.employee"].create([
        { employee_id: this.data.employeePierreId },
    ]);
});

test("many2one_avatar_employee widget in kanban view with skills on avatar card", async () => {
    await start();
    await openKanbanView("m2o.avatar.employee", {
        arch: `<kanban>
            <templates>
                <t t-name="kanban-box">
                    <div>
                        <field name="employee_id" widget="many2one_avatar_employee"/>
                    </div>
                </t>
            </templates>
        </kanban>`,
    });

    await contains(".o_m2o_avatar", { count: 1 });

    // Kanban card should display employee avatar
    await contains(".o_field_many2one_avatar_employee img", { count: 1 });
    expect(
        queryAttribute(".o_kanban_record .o_field_many2one_avatar_employee img", "data-src")
    ).toBe(`/web/image/hr.employee/${this.data.employeePierreId}/avatar_128`);

    // Clicking on employee avatar to display avatar card
    await click(".o_kanban_record .o_m2o_avatar");
    await contains(".o_avatar_card");
    await contains(".o_avatar_card .o_employee_skills_tags > .o_tag", { count: 2 }); // Skills should be listed in the card
});
