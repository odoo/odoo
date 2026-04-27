/** @odoo-module **/

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { start } from "@mail/../tests/helpers/test_utils";
import { contains } from "@web/../tests/utils";
import { click } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";


QUnit.module("M2OAvatarResourceWidgetTests", {
    async beforeEach() {
        this.serverData = {};
        setupViewRegistries();

        /* 1. Create data
           two type of records tested:
            - 2 planning slots linked to a human resource not linked to a user:
              the hr employee status should be displayed in avatar card popover
            - 2 planning slots linked to a human resource linked to a user:
              the im status of the user should be displayed in avatar card popover
        */

        const pyEnv = await startServer();
        this.pyEnv = pyEnv;
        this.data = {};

        // Users
        [this.data.partnerLucindaId, this.data.partnerCardenioId] = pyEnv["res.partner"].create([{
            name: "Lucinda",
        }, {
            name: "Cardenio",
        }]);
        [this.data.userLucindaId, this.data.userCardenioId] = pyEnv["res.users"].create([{
            name: "Lucinda",
            partner_id: this.data.partnerLucindaId,
        }, {
            name: "Cardenio",
            partner_id: this.data.partnerCardenioId,
        }]);

        // Resources
        [this.data.resourceDorotheaId, this.data.resourceFernandoId, this.data.resourceLucindaId, this.data.resourceCardenioId] = pyEnv["resource.resource"].create([{
            name: "Dorothea",
            resource_type: "user",
            hr_icon_display: "presence_holiday_present",
            show_hr_icon_display: true,
        }, {
            name: "Fernando",
            resource_type: "user",
            hr_icon_display: "presence_holiday_absent",
            show_hr_icon_display: true,
        }, {
            name: "Lucinda",
            resource_type: "user",
            user_id: this.data.userLucindaId,
            im_status: "leave_online",
        }, {
            name: "Cardenio",
            resource_type: "user",
            user_id: this.data.userCardenioId,
            im_status: "leave_away",
        }]);

        // Employees
        const employeeDorotheaData = {
            name: "Dorothea",
        };
        const employeeFernandoData = {
            name: "Fernando",
        };
        const employeeLucindaData = {
            name: "Lucinda",
            user_id: this.data.userLucindaId,
            user_partner_id: this.data.partnerLucindaId,
        };
        const employeeCardenioData = {
            name: "Cardenio",
            user_id: this.data.userCardenioId,
            user_partner_id: this.data.partnerCardenioId,
        };
        pyEnv["hr.employee"].create([{
            ...employeeDorotheaData,
            resource_id: this.data.resourceDorotheaId,
        }, {
            ...employeeFernandoData,
            resource_id: this.data.resourceFernandoId,
        }, {
            ...employeeLucindaData,
            resource_id: this.data.resourceLucindaId,
        }, {
            ...employeeCardenioData,
            resource_id: this.data.resourceCardenioId,
        }]);

        // Imitating the server behavior by creating an hr.employee.public record with the same data and same id
        [this.data.employeeDorotheaId,
         this.data.employeeFernandoId,
         this.data.employeeLucindaId,
         this.data.employeeCardenioId] = pyEnv["hr.employee.public"].create([
             employeeDorotheaData,
             employeeFernandoData,
             employeeLucindaData,
             employeeCardenioData
         ]);

        // Planning slots
        [this.data.planning1Id,
         this.data.planning2Id,
         this.data.planning3Id,
         this.data.planning4Id] = pyEnv["planning.slot"].create([{
            display_name: "Planning slot Dorothea",
            resource_id: this.data.resourceDorotheaId,
            resource_type: "user",
            user_id: false,
        }, {
            display_name: "Planning slot Fernando",
            resource_id: this.data.resourceFernandoId,
            resource_type: "user",
            user_id: false,
        }, {
            display_name: "Planning Slot Lucinda",
            resource_id: this.data.resourceLucindaId,
            resource_type: "user",
            user_id: this.data.userLucindaId,
        }, {
            display_name: "Planning Slot Cardenio",
            resource_id: this.data.resourceCardenioId,
            resource_type: "user",
            user_id: this.data.userCardenioId,
        }]);
    },
}, () => {
    QUnit.test("many2one_avatar_resource widget in list view with time-off idle", async function (assert) {
        const mockRPC = (route, args) => {
            if (route === "/web/dataset/call_kw/resource.resource/get_avatar_card_data") {
                // const resourceIdArray = params.args[0];
                const resourceId = args.args[0];
                const resources = this.pyEnv['resource.resource'].search_read([['id', '=', resourceId[0]]]);

                const result = resources.map(resource => ({
                    name: resource.name,
                    employee_id: resource.employee_id,
                    user_id: resource.user_id,
                    show_hr_icon_display: resource.show_hr_icon_display,
                    hr_icon_display: resource.hr_icon_display,
                    im_status: resource.im_status,
                }));
                return result;
            }
        };

        this.serverData.views = {
            "planning.slot,false,list": `
                    <list>
                        <field name="display_name"/>
                        <field name="resource_id" widget="many2one_avatar_resource"/>
                    </list>`,
        };
        const { openView } = await start({ serverData: this.serverData, mockRPC });
        await openView({
            res_model: "planning.slot",
            views: [[false, "list"]],
        });

        // 1. Clicking on human resource's avatar with no user associated (status: presence_holiday_present)
        await click(document.querySelector(".o_m2o_avatar"));
        await contains(".o_card_user_infos span", { text: "Dorothea" });
        await contains(
            ".o_employee_presence_status .fa-plane.text-success", {},
            "The idle icon of a present employee on leave should be a green plane"
        );

        // 2. Clicking on human resource's avatar with no user associated (status: presence_holiday_absent)
        await click(document.querySelectorAll(".o_m2o_avatar")[1]);
        await contains(".o_card_user_infos span", { text: "Fernando" });
        await contains(
            ".o_employee_presence_status .fa-plane.text-warning", {},
            "The idle icon of an absent employee on leave should be an orange plane"
        );

        // 3. Clicking on human resource's avatar with a user associated (status: leave_online)
        await click(document.querySelectorAll(".o_m2o_avatar")[2]);
        await contains(".o_card_user_infos span", { text: "Lucinda" });
        await contains(
            ".o_user_im_status .fa-plane.text-success", {},
            "The idle icon of a connected user on leave should be a green plane"
        );

        // 4. Clicking on human resource's avatar with a user associated (status: leave_away)
        await click(document.querySelectorAll(".o_m2o_avatar")[3]);
        await contains(".o_card_user_infos span", { text: "Cardenio" });
        await contains(
            ".o_user_im_status .fa-plane.text-warning", {},
            "The idle icon of a afk user on leave should be an orange plane"
        );
    });
});
