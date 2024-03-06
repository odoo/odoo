import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { openFormView, start } from "@mail/../tests/helpers/test_utils";
import { click } from "@web/../tests/helpers/utils";
import { contains } from "@web/../tests/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";


QUnit.module("M2OAvatarResourceWidgetTests", {
    async beforeEach() {
        this.serverData = {};
        setupViewRegistries();

        /* 1. Create data
           3 type of records tested:
            - Task linked to a material resource (resourceComputer)
                - fa-wrench should be used instead of avatar
                - clicking the icon should not open any popover
            - Task linked to a human resource not linked to a user (resourceMarie)
                (- avatar of the resource should not be displayed)
                (Currently not implemented, todo when m2o fields will support relatedFields option)
                - a card popover should open
                - No possibility to send a message to this resource as no user exists for it
            - Task linked to a human resource linked to a user (resourcePierre)
                - avatar of the user should be displayed
                - a card popover should open
                - A button to send a message to this user should be on the card
        */

        const pyEnv = await startServer();
        this.data = {};

        // User
        this.data.partnerPierreId = pyEnv["res.partner"].create({
            name: "Pierre",
        });
        this.data.userPierreId = pyEnv["res.users"].create({
            name: "Pierre",
            partner_id: this.data.partnerPierreId,
        });

        // Resources
        [this.data.resourceComputerId,
         this.data.resourceMarieId,
         this.data.resourcePierreId] = pyEnv["resource.resource"].create([{
            name: "Continuity testing computer",
            resource_type: "material",
        }, {
            name: "Marie",
            resource_type: "user",
        }, {
            name: "Pierre",
            resource_type: "user",
            user_id: this.data.userPierreId,
            email: "Pierre@odoo.test",
            im_status: "online",
            phone: "+32487898933",
        }]);

        // Tasks linked to those resources
        [this.data.taskComputerId,
         this.data.taskMarieId,
         this.data.taskPierreId] = pyEnv["resource.task"].create([{
            display_name: "Task testing computer",
            resource_id: this.data.resourceComputerId,
            resource_type: "material",
        }, {
            display_name: "Task Marie",
            resource_id: this.data.resourceMarieId,
            resource_type: "user",
        }, {
            display_name: "Task Pierre",
            resource_id: this.data.resourcePierreId,
            resource_type: "user",
        }]);
    },
}, () => {
    QUnit.test("many2one_avatar_resource widget in form view", async function (assert) {
        assert.expect(1);

        this.serverData.views = {
            "resource.task,false,form": `<form string="Partners">
                    <field name="display_name"/>
                    <field name="resource_id" widget="many2one_avatar_resource"/>
                </form>`,
        };
        await start({ serverData: this.serverData });
        await openFormView("resource.task", this.data.taskComputerId);

        assert.hasClass(
            document.querySelector(".o_material_resource"),
            "o_material_resource",
            "material icon should be displayed"
        );
    });

    QUnit.test("many2one_avatar_resource widget in kanban view", async function (assert) {
        this.serverData.views = {
            "resource.task,false,kanban": `
                    <kanban>
                        <templates>
                            <t t-name="kanban-box">
                                <div>
                                    <field name="display_name"/>
                                    <field name="resource_id" widget="many2one_avatar_resource"/>
                                </div>
                            </t>
                        </templates>
                    </kanban>`,
        };
        const { openView } = await start({ serverData: this.serverData });
        await openView({
            res_model: "resource.task",
            views: [[false, "kanban"]],
        });

        assert.containsN(document.body, ".o_m2o_avatar", 3);

        // fa-wrench should be displayed for the first task
        await contains(".o_m2o_avatar > span.o_material_resource > i.fa-wrench");

        // Second and third slots should display employee avatar
        assert.containsN(
            document.body,
            ".o_field_many2one_avatar_resource img",
            2,
        );
        assert.strictEqual(
            document.querySelector(".o_kanban_record:nth-of-type(2) .o_field_many2one_avatar_resource img").getAttribute("data-src"),
            "/web/image/resource.resource/" + this.data.resourceMarieId + "/avatar_128",
        );
        assert.strictEqual(
            document.querySelector(".o_kanban_record:nth-of-type(3) .o_field_many2one_avatar_resource img").getAttribute("data-src"),
            "/web/image/resource.resource/" + this.data.resourcePierreId + "/avatar_128",
        );

        // 1. Clicking on material resource's icon
        await click(document.querySelector(".o_kanban_record:nth-of-type(1) .o_m2o_avatar"));
        assert.containsNone(document.body, ".o_avatar_card");

        // 2. Clicking on human resource's avatar with no user associated
        await click(document.querySelector(".o_kanban_record:nth-of-type(2) .o_m2o_avatar"));
        await contains(".o_card_user_infos span", { text: "Marie" });
        await contains(".o_avatar_card", { count: 1 }, "Only one popover resource card should be opened at a time");
        await contains(
            ".o_avatar_card_buttons button",
            { text: "Send message", count: 0 },
            'No "Send Message" button should be displayed for this employee as it is linked to no user',
        );

        // 3. Clicking on human resource's avatar with one user associated
        await click(document.querySelector(".o_kanban_record:nth-of-type(3) .o_m2o_avatar"));
        await contains(".o_card_user_infos span", { text: "Pierre" });
        await contains(".o_avatar_card", { count: 1 }, "Only one popover resource card should be opened at a time");
        await contains(".o_card_user_infos > a", { text: "Pierre@odoo.test" });
        await contains(".o_card_user_infos > a", { text: "+32487898933" });
        assert.strictEqual(document.querySelector(".o_avatar_card_buttons button").textContent, "Send message");
        await click(document.querySelector(".o_avatar_card_buttons button"));
        await contains(".o-mail-ChatWindow");
        assert.strictEqual(
            document.querySelector(".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate").textContent,
            "Pierre"
        );
    });
});
