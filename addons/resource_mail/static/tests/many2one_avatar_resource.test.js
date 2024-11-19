import { defineResourceModels } from "@resource/../tests/resource_test_helpers";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryFirst } from "@odoo/hoot-dom";
import {
    click,
    contains,
    openFormView,
    openKanbanView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

describe.current.tags("desktop");
const data = {};
defineResourceModels();
beforeEach(async () => {
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
    [data.taskComputerId, data.taskMarieId, data.taskPierreId] = pyEnv["resource.task"].create([
        {
            display_name: "Task testing computer",
            resource_id: data.resourceComputerId,
            resource_type: "material",
        },
        {
            display_name: "Task Marie",
            resource_id: data.resourceMarieId,
            resource_type: "user",
        },
        {
            display_name: "Task Pierre",
            resource_id: data.resourcePierreId,
            resource_type: "user",
        },
    ]);
});

test("many2one_avatar_resource widget in form view", async () => {
    await start();
    await openFormView("resource.task", data.taskComputerId, {
        arch: `<form string="Partners">
                <field name="display_name"/>
                <field name="resource_id" widget="many2one_avatar_resource"/>
            </form>`,
    });
    expect(queryFirst(".o_material_resource")).toHaveClass("o_material_resource");
});

test("many2one_avatar_resource widget in kanban view", async () => {
    await start();
    await openKanbanView("resource.task", {
        arch: `<kanban>
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                        <field name="resource_id" widget="many2one_avatar_resource"/>
                    </t>
                </templates>
            </kanban>`,
    });
    await contains(".o_m2o_avatar", { count: 3 });
    // fa-wrench should be displayed for the first task
    await contains(".o_m2o_avatar > span.o_material_resource > i.fa-wrench");
    // Second and third slots should display employee avatar
    await contains(".o_field_many2one_avatar_resource img", { count: 2 });
    expect(queryFirst(".o_field_many2one_avatar_resource img").getAttribute("data-src")).toBe(
        "/web/image/resource.resource/" + data.resourceMarieId + "/avatar_128"
    );
    expect(
        queryFirst(
            ".o_kanban_record:nth-of-type(3) .o_field_many2one_avatar_resource img"
        ).getAttribute("data-src")
    ).toBe("/web/image/resource.resource/" + data.resourcePierreId + "/avatar_128");
    // 1. Clicking on material resource's icon
    await click(".o_kanban_record:nth-of-type(1) .o_m2o_avatar");
    await contains(".o_avatar_card", { count: 0 });
    // 2. Clicking on human resource's avatar with no user associated
    await click(".o_kanban_record:nth-of-type(2) .o_m2o_avatar");
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
    await click(".o_kanban_record:nth-of-type(3) .o_m2o_avatar");
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
