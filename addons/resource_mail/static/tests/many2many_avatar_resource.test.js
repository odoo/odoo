import {
    click,
    contains,
    openFormView,
    openListView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";
import { defineResourceModels } from "@resource/../tests/resource_test_helpers";

describe.current.tags("desktop");
const data = {};
defineResourceModels();
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

    // Task linked to those resources
    data.task1Id = pyEnv["resource.task"].create({
        display_name: "Task with three resources",
        resource_ids: [data.resourceComputerId, data.resourceMarieId, data.resourcePierreId],
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
    expect(
        ".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate:first"
    ).toHaveText("Pierre");
});

test("many2many_avatar_resource widget in list view", async () => {
    await start();
    await openListView("resource.task", {
        arch: '<list><field name="display_name"/><field name="resource_ids" widget="many2many_avatar_resource"/></list>',
    });
    await contains(
        ".o_m2m_avatar",
        { count: 2 },
        "Two human resources with avatar should be displayed"
    );
    await contains(
        "i.fa-wrench",
        { count: 1 },
        "Two material resources with fa-wrench icon should be displayed"
    );
    // Second and third records in widget should display employee avatars
    expect(".many2many_tags_avatar_field_container .o_tag img:eq(0)").toHaveAttribute(
        "data-src",
        `/web/image/resource.resource/${data.resourceMarieId}/avatar_128`
    );
    expect(".many2many_tags_avatar_field_container .o_tag img:eq(1)").toHaveAttribute(
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
    expect(
        ".o-mail-ChatWindow-header button.o-dropdown.o-mail-ChatWindow-command > .text-truncate:first"
    ).toHaveText("Pierre");
});
