import {
    click,
    contains,
    openFormView,
    openListView,
    openKanbanView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryAll, queryFirst } from "@odoo/hoot-dom";
import { defineResourceMailModels } from "./resource_mail_test_helpers";
import { onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
const data = {};
defineResourceMailModels();
beforeEach(async () => {
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

    // User
    data.partnerPierreId = pyEnv["res.partner"].create({
        name: "Pierre",
        email: "Pierre@odoo.test",
        phone: "+32487898933",
    });
    data.userPierreId = pyEnv["res.users"].create({
        name: "Pierre",
        partner_id: data.partnerPierreId,
    });

    // Resources
    [data.resourceComputerId, data.resourceMarieId, data.resourcePierreId] = pyEnv[
        "resource.resource"
    ].create([
        {
            name: "Continuity testing computer",
            resource_type: "material",
        },
        {
            name: "Marie",
            resource_type: "user",
        },
        {
            name: "Pierre",
            resource_type: "user",
            user_id: data.userPierreId,
            im_status: "online",
        },
    ]);

    // Tasks linked to those resources
    [ data.task1Id, data.task2Id ] = pyEnv["resource.task"].create([{
        display_name: "Task with three resources",
        resource_ids: [data.resourceComputerId, data.resourceMarieId, data.resourcePierreId],
    }, {
        display_name: "Task with one resources",
        resource_ids: [
            data.resourcePierreId,
        ],
    }]);

    onRpc("resource.resource", "get_avatar_card_data", (params) => {
        const resourceIdArray = params.args[0];
        const resourceId = resourceIdArray[0];
        const resources = pyEnv['resource.resource'].read([resourceId]);
        const result = resources.map(resource => ({
            name: resource.name,
            role_ids: resource.role_ids,
            email:resource.email,
            phone: resource.phone,
            user_id: resource.user_id,
        }));
        return result;
    });
});
test("many2many_avatar_resource widget in form view", async () => {
    await start();
    await openFormView("resource.task", data.task1Id, {
        arch: `<form string="Tasks">
                <field name="display_name"/>
                <field name="resource_ids" widget="many2many_avatar_resource"/>
            </form>`,
    });
    await contains("img.o_m2m_avatar", { count: 2 });
    await contains(".fa-wrench", { count: 1 });
    // Second and third records in widget should display employee avatars
    const avatarImages = queryAll(".many2many_tags_avatar_field_container .o_tag img");
    expect(avatarImages[0]).toHaveAttribute(
        "data-src",
        `/web/image/resource.resource/${data.resourceMarieId}/avatar_128`
    );
    expect(avatarImages[1]).toHaveAttribute(
        "data-src",
        `/web/image/resource.resource/${data.resourcePierreId}/avatar_128`
    );
    // 1. Clicking on material resource's icon
    await click(".many2many_tags_avatar_field_container .o_tag i.fa-wrench");
    await contains(".o_avatar_card", { count: 0 });

    // 2. Clicking on human resource's avatar with no user associated
    await click(".many2many_tags_avatar_field_container .o_tag img:first");
    await contains(".o_card_user_infos span", { text: "Marie" });
    await contains(
        ".o_avatar_card",
        { count: 1 },
        "Only one popover resource card should be opened at a time"
    );
    await contains(
        ".o_avatar_card_buttons button",
        { text: "Send message", count: 0 },
        'No "Send Message" button should be displayed for this employee as it is linked to no user'
    );
    // 3. Clicking on human resource's avatar with one user associated
    await click(queryAll(".many2many_tags_avatar_field_container .o_tag img")[1]);
    await contains(".o_card_user_infos span", { text: "Pierre" });
    await contains(
        ".o_avatar_card",
        { count: 1 },
        "Only one popover resource card should be opened at a time"
    );
    await contains(".o_card_user_infos > a", { text: "Pierre@odoo.test" });
    await contains(".o_card_user_infos > a", { text: "+32487898933" });
    expect(".o_avatar_card_buttons button:first").toHaveText("Send message");
    await click(".o_avatar_card_buttons button");
    await contains(".o-mail-ChatWindow");
    expect(".o-mail-ChatWindow-moreActions > .text-truncate:first").toHaveText("Pierre");
});

test("many2many_avatar_resource widget in list view", async () => {
    await start();
    await openListView("resource.task", {
        arch: '<list><field name="display_name"/><field name="resource_ids" widget="many2many_avatar_resource"/></list>',
    });

    const [ row1, row2 ] = queryAll(".o_data_row");
    await contains(
        "img.o_m2m_avatar",
        { count: 2, target: row1 },
        "Two human resources with avatar should be displayed",
    );
    await contains(
        "i.fa-wrench.o_m2m_avatar",
        { count: 1, target: row1 },
        "One material resource with fa-wrench icon should be displayed",
    );
    await contains(
        "div.o_tag_badge_text",
        { count: 0, target: row1 },
        "No text should be displayed on any avatar",
    );

    await contains(
        "img.o_m2m_avatar",
        { count: 1, target: row2 },
        "One human resource with avatar should be displayed",
    );
    await contains(
        "div.o_tag_badge_text",
        { count: 1, target: row2 },
        "The text should be displayed on the avatar",
    );

    // Second and third records in widget should display employee avatars
    const [ tagMarie, tagPierre ] = document.querySelectorAll(".many2many_tags_avatar_field_container .o_tag img");
    expect(tagMarie).toHaveAttribute("data-src", `/web/image/resource.resource/${data.resourceMarieId}/avatar_128`);
    expect(tagPierre).toHaveAttribute("data-src", `/web/image/resource.resource/${data.resourcePierreId}/avatar_128`);
    // 1. Clicking on material resource's icon
    await click(".many2many_tags_avatar_field_container .o_tag i.fa-wrench");
    await contains(".o_avatar_card", { count: 0 });
    // 2. Clicking on human resource's avatar with no user associated
    await click(tagMarie);
    await contains(".o_card_user_infos span", { text: "Marie" });
    await contains(
        ".o_avatar_card",
        { count: 1 },
        "Only one popover resource card should be opened at a time"
    );
    await contains(
        ".o_avatar_card_buttons button",
        { text: "Send message", count: 0 },
        'No "Send Message" button should be displayed for this employee as it is linked to no user'
    );
    // 3. Clicking on human resource's avatar with one user associated
    await click(tagPierre);
    await contains(".o_card_user_infos span", { text: "Pierre" });
    await contains(
        ".o_avatar_card",
        { count: 1 },
        "Only one popover resource card should be opened at a time"
    );
    await contains(".o_card_user_infos > a", { text: "Pierre@odoo.test" });
    await contains(".o_card_user_infos > a", { text: "+32487898933" });
    expect(queryFirst(".o_avatar_card_buttons button").textContent).toBe("Send message");
    await click(".o_avatar_card_buttons button");
    await contains(".o-mail-ChatWindow");
    expect(queryFirst(".o-mail-ChatWindow-moreActions > .text-truncate").textContent).toBe(
        "Pierre"
    );
});


test("many2many_avatar_resource widget in kanban view", async () => {
    await start();
    await openKanbanView("resource.task", {
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <div class="oe_kanban_global_click container">
                            <div class="oe_kanban_content">
                                <field name="display_name"/>
                                <div class="o_kanban_record_bottom">
                                    <field name="resource_ids" widget="many2many_avatar_resource"/>
                                </div>
                            </div>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });

    const [ card1, card2 ] = queryAll(".oe_kanban_content");
    await contains(
        "img.o_m2m_avatar",
        { count: 2, target: card1 },
        "Two human resources with avatar should be displayed",
    );
    await contains(
        "i.fa-wrench.o_m2m_avatar",
        { count: 1, target: card1 },
        "One material resource with fa-wrench icon should be displayed",
    );
    await contains(
        "div.o_tag_badge_text",
        { count: 0, target: card1 },
        "No text should be displayed on any avatar",
    );

    await contains(
        "img.o_m2m_avatar",
        { count: 1, target: card2 },
        "One human resource with avatar should be displayed",
    );
    await contains(
        "div.o_tag_badge_text",
        { count: 0, target: card2 },
        "No text should be displayed on the avatar",
    );

    // Second and third records in widget should display employee avatars
    const [ tagMarie, tagPierre ] = document.querySelectorAll(".many2many_tags_avatar_field_container .o_tag img");
    expect(tagMarie).toHaveAttribute("data-src", `/web/image/resource.resource/${data.resourceMarieId}/avatar_128`);
    expect(tagPierre).toHaveAttribute("data-src", `/web/image/resource.resource/${data.resourcePierreId}/avatar_128`);
    // 1. Clicking on material resource's icon
    await click(".many2many_tags_avatar_field_container .o_tag i.fa-wrench");
    await contains(".o_avatar_card", { count: 0 });
    // 2. Clicking on human resource's avatar with no user associated
    await click(tagMarie);
    await contains(".o_card_user_infos span", { text: "Marie" });
    await contains(
        ".o_avatar_card",
        { count: 1 },
        "Only one popover resource card should be opened at a time"
    );
    await contains(
        ".o_avatar_card_buttons button",
        { text: "Send message", count: 0 },
        'No "Send Message" button should be displayed for this employee as it is linked to no user'
    );
    // 3. Clicking on human resource's avatar with one user associated
    await click(tagPierre);
    await contains(".o_card_user_infos span", { text: "Pierre" });
    await contains(
        ".o_avatar_card",
        { count: 1 },
        "Only one popover resource card should be opened at a time"
    );
    await contains(".o_card_user_infos > a", { text: "Pierre@odoo.test" });
    await contains(".o_card_user_infos > a", { text: "+32487898933" });
    expect(".o_avatar_card_buttons button:first").toHaveText("Send message");
    await click(".o_avatar_card_buttons button");
    await contains(".o-mail-ChatWindow");
    expect(".o-mail-ChatWindow-moreActions > .text-truncate:first").toHaveText("Pierre");
});
