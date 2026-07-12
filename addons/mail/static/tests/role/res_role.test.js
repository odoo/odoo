import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    openListView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, expect, test, waitFor } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";

describe.current.tags("desktop");
defineMailModels();

test("Author names are colored according to the author's role.", async () => {
    const pyEnv = await startServer();
    /**
     * Create multiple roles to assert precedence rules.
     * The color of the author name is the color of the user's role that:
     * 1. has a color
     * 2. has the lowest sequence
     * 3. has the lowest id
     */
    const [roleId1, roleId2, roleId3, roleId4] = pyEnv["res.role"].create([
        { name: "no color", color: undefined, sequence: 1 },
        { name: "green", color: "#008000", sequence: 1000 },
        { name: "red", color: "#FF0000", sequence: 10 },
        { name: "blue", color: "#0000FF", sequence: 10 },
    ]);
    const partnerId = pyEnv["res.partner"].create({ name: "COLOR ME" });
    pyEnv["res.users"].create([
        // Link several users to the author to test that the role is resolved from all associated users.
        { name: "Michel", role_ids: [roleId1, roleId2], partner_id: partnerId },
        { name: "michel93", role_ids: [roleId4, roleId3], partner_id: partnerId },
    ]);
    const channelId = pyEnv["discuss.channel"].create({ name: "some-channel" });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        res_id: channelId,
        model: "discuss.channel",
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Message-author :text(COLOR ME)");
    const authorNameEl = queryOne(".o-mail-Message-author :text(COLOR ME)");
    expect(getComputedStyle(authorNameEl).color).toBe("rgb(255, 0, 0)");
});

test("RoleColorBadge previews the role's assigned color.", async () => {
    const pyEnv = await startServer();
    pyEnv["res.role"].create({ color: "#008000" });
    await start();
    await openListView("res.role", {
        arch: `<list><field name="color" widget="mail_role_color_badge"/></list>`,
    });
    await waitFor(".o_field_mail_role_color_badge button");
    const buttonEl = queryOne(".o_field_mail_role_color_badge button");
    expect(getComputedStyle(buttonEl).backgroundColor).toBe("rgb(0, 128, 0)");
});

test("Selecting a color from the RoleColorBadge picker updates the role's color.", async () => {
    const targetColor = "#FF00FF";
    const pyEnv = await startServer();
    pyEnv["res.role"].create({});
    await start();
    await openListView("res.role", {
        arch: `<list><field name="color" widget="mail_role_color_badge"/></list>`,
    });
    await click(".o_field_mail_role_color_badge button");
    await click(`.o_color_picker_button[data-color="${targetColor}"]`);
    await contains(`.o_field_mail_role_color_badge button[data-color="${targetColor}"]`);
});

test("RoleColorBadge is disabled if the user can't write to the record.", async () => {
    const pyEnv = await startServer();
    pyEnv["res.role"].create({});
    await start();
    await openListView("res.role", {
        // readonly="True" to simulate insufficient access rights
        arch: `<list><field name="color" widget="mail_role_color_badge" readonly="True"/></list>`,
    });
    await contains(".o_field_mail_role_color_badge button:disabled");
});
