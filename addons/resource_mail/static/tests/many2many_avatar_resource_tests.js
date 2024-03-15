/** @odoo-module **/

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { openFormView, start } from "@mail/../tests/helpers/test_utils";
import { contains } from "@web/../tests/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { click } from "@web/../tests/helpers/utils";


QUnit.module("M2MAvatarResourceWidgetTests", {
    async beforeEach() {
        this.serverData = {};
        setupViewRegistries();

        /* 1. Create data
           3 type of resources will be tested in the widget:
            - material resource (resourceComputer)
                - fa-wrench should be used instead of avatar
                - clicking the icon should not open any popover
            - human resource not linked to a user (resourceMarie)
                (- avatar of the resource should not be displayed)
                (Currently not implemented to stay in line with m2o widget)
                - a card popover should open
                - No possibility to send a message to this resource as no user exists for it
            - human resource linked to a user (resourcePierre)
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

        // Task linked to those resources 
        this.data.task1Id = pyEnv["resource.task"].create({
            display_name: "Task with three resources",
            resource_ids: [
                this.data.resourceComputerId,
                this.data.resourceMarieId,
                this.data.resourcePierreId,
            ],
        });
    },
}, () => {
    QUnit.test("many2many_avatar_resource widget in form view", async function (assert) {
        this.serverData.views = {
            "resource.task,false,form": `
                <form string="Tasks">
                    <field name="display_name"/>
                    <field name="resource_ids" widget="many2many_avatar_resource"/>
                </form>`,
        };

        await start({ serverData: this.serverData });
        await openFormView("resource.task", this.data.task1Id);
        assert.containsN(document.body, "img.o_m2m_avatar", 2);
        assert.containsN(document.body, ".fa-wrench", 1);

        // Second and third records in widget should display employee avatars
        const avatarImages = document.querySelectorAll(".many2many_tags_avatar_field_container .o_tag img");
        assert.strictEqual(
            avatarImages[0].getAttribute("data-src"),
            "/web/image/resource.resource/" + this.data.resourceMarieId + "/avatar_128",
        );
        assert.strictEqual(
            avatarImages[1].getAttribute("data-src"),
            "/web/image/resource.resource/" + this.data.resourcePierreId + "/avatar_128",
        );

        // 1. Clicking on material resource's icon
        await click(document.querySelector(".many2many_tags_avatar_field_container .o_tag i.fa-wrench"));
        assert.containsNone(document.body, ".o_avatar_card");

        // 2. Clicking on human resource's avatar with no user associated
        await click(document.querySelector(".many2many_tags_avatar_field_container .o_tag img"));
        await contains(".o_card_user_infos span", { text: "Marie" });
        await contains(".o_avatar_card", { count: 1 }, "Only one popover resource card should be opened at a time");
        await contains(
            ".o_avatar_card_buttons button",
            { text: "Send message", count: 0 },
            'No "Send Message" button should be displayed for this employee as it is linked to no user',
        );

        // 3. Clicking on human resource's avatar with one user associated
        await click(document.querySelectorAll(".many2many_tags_avatar_field_container .o_tag img")[1]);
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

    QUnit.test("many2many_avatar_resource widget in list view", async function (assert) {
        this.serverData.views = {
            "resource.task,false,list": `
                    <tree>
                        <field name="display_name"/>
                        <field name="resource_ids" widget="many2many_avatar_resource"/>
                    </tree>`,
        };
        const { openView } = await start({ serverData: this.serverData });
        await openView({
            res_model: "resource.task",
            views: [[false, "list"]],
        });

        assert.containsN(document.body, ".o_m2m_avatar", 2, "Two human resources with avatar should be displayed");
        assert.containsN(document.body, "i.fa-wrench", 1, "Two material resources with fa-wrench icon should be displayed");

        // Second and third records in widget should display employee avatars
        assert.strictEqual(
            document.querySelector(".many2many_tags_avatar_field_container .o_tag img").getAttribute("data-src"),
            "/web/image/resource.resource/" + this.data.resourceMarieId + "/avatar_128",
        );
        assert.strictEqual(
            document.querySelectorAll(".many2many_tags_avatar_field_container .o_tag img")[1].getAttribute("data-src"),
            "/web/image/resource.resource/" + this.data.resourcePierreId + "/avatar_128",
        );

        // 1. Clicking on material resource's icon
        await click(document.querySelector(".many2many_tags_avatar_field_container .o_tag i.fa-wrench"));
        assert.containsNone(document.body, ".o_avatar_card");

        // 2. Clicking on human resource's avatar with no user associated
        await click(document.querySelector(".many2many_tags_avatar_field_container .o_tag img"));
        await contains(".o_card_user_infos span", { text: "Marie" });
        await contains(".o_avatar_card", { count: 1 }, "Only one popover resource card should be opened at a time");
        await contains(
            ".o_avatar_card_buttons button",
            { text: "Send message", count: 0 },
            'No "Send Message" button should be displayed for this employee as it is linked to no user',
        );

        // 3. Clicking on human resource's avatar with one user associated
        await click(document.querySelectorAll(".many2many_tags_avatar_field_container .o_tag img")[1]);
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
