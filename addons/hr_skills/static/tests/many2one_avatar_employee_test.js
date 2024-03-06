/** @odoo-module **/

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { start } from "@mail/../tests/helpers/test_utils";
import { patchWithCleanup, click } from "@web/../tests/helpers/utils";
import { contains } from "@web/../tests/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";

import { patchAvatarCardPopover } from "@hr/components/avatar_card/avatar_card_popover_patch";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";
import { patchAvatarCardResourcePopover } from "@hr_skills/components/avatar_card_resource/avatar_card_resource_popover_patch";
import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";

QUnit.module(
    "M2OAvatarEmployeeWidgetTestsSkills",
    {
        /* Main Goals of these tests:
        - Test the integration of skills on the avatar card of employees, even if Planning is not installed
     */
        async beforeEach() {
            this.serverData = {};
            setupViewRegistries();
            patchWithCleanup(AvatarCardPopover.prototype, patchAvatarCardPopover);
            patchWithCleanup(AvatarCardResourcePopover.prototype, patchAvatarCardResourcePopover);

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
            const employeePierreData = {
                name: "Pierre",
                user_id: this.data.user1Id,
                user_partner_id: this.data.partner1Id,
            };
            this.data.employeePierreId = pyEnv["hr.employee"].create(employeePierreData);

            // Employee skills
            [this.data.employeeSkill1Id, this.data.employeeSkill2Id] = pyEnv[
                "hr.employee.skill"
            ].create([
                {
                    employee_id: this.data.employeePierreId,
                    skill_id: this.data.skillJavaId,
                    display_name: "Java",
                },
                {
                    employee_id: this.data.employeePierreId,
                    skill_id: this.data.skillTigrinyaId,
                    display_name: "Tigrinya",
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
        },
    },
    () => {
        QUnit.test(
            "many2one_avatar_employee widget in kanban view with skills on avatar card",
            async function (assert) {
                this.serverData.views = {
                    "m2o.avatar.employee,false,kanban": `
                    <kanban>
                        <templates>
                            <t t-name="kanban-box">
                                <div>
                                    <field name="employee_id" widget="many2one_avatar_employee"/>
                                </div>
                            </t>
                        </templates>
                    </kanban>`,
                };
                const { openView } = await start({ serverData: this.serverData });
                await openView({
                    res_model: "m2o.avatar.employee",
                    views: [[false, "kanban"]],
                });

                assert.containsN(document.body, ".o_m2o_avatar", 1);

                // Kanban card should display employee avatar
                assert.containsN(document.body, ".o_field_many2one_avatar_employee img", 1);
                assert.strictEqual(
                    document
                        .querySelector(".o_kanban_record .o_field_many2one_avatar_employee img")
                        .getAttribute("data-src"),
                    `/web/image/hr.employee.public/${this.data.employeePierreId}/avatar_128`
                );

                // Clicking on employee avatar to display avatar card
                await click(document.querySelector(".o_kanban_record .o_m2o_avatar"));
                await contains(".o_avatar_card");
                assert.containsN(
                    document.body,
                    ".o_avatar_card .o_employee_skills_tags > .o_tag",
                    2
                ); // Skills should be listed in the card
            }
        );
    }
);
