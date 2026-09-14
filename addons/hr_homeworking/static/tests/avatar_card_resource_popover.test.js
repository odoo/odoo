import { describe, expect, test } from "@odoo/hoot";
import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";
import { defineResourceMailModels } from "@resource_mail/../tests/resource_mail_test_helpers";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { start, startServer } from "@mail/../tests/mail_test_helpers";

describe.current.tags("desktop");
defineResourceMailModels();

async function mountCard(im_status) {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Located worker" });
    const resourceId = pyEnv["resource.resource"].create({
        name: "Located worker",
        resource_type: "user",
        user_id: userId,
    });
    onRpc("resource.resource", "get_avatar_card_data", () => [
        { name: "Located worker", user_id: [userId, "Located worker"], im_status },
    ]);
    await start();
    await mountWithCleanup(AvatarCardResourcePopover, {
        props: { id: resourceId, close: () => {} },
    });
}

test("a located status renders its icon on the avatar card", async () => {
    await mountCard("home_online");
    expect(".o_user_im_status .fa-house").toHaveCount(1);
    expect(".o_user_im_status .fa-house").toHaveClass("text-success");
    expect(".o_user_im_status .fa-question-circle").toHaveCount(0);
});

test("a located BUSY status renders an icon, which it did not before", async () => {
    await mountCard("office_busy");
    expect(".o_user_im_status .fa-building").toHaveCount(1);
    expect(".o_user_im_status .fa-building").toHaveClass("text-danger");
    expect(".o_user_im_status .fa-question-circle").toHaveCount(0);
});

test("home_away renders on the avatar card", async () => {
    await mountCard("home_away");
    expect(".o_user_im_status .fa-house").toHaveCount(1);
    expect(".o_user_im_status .fa-house").toHaveClass("o-yellow");
    expect(".o_user_im_status .fa-question-circle").toHaveCount(0);
});

test("office_offline renders on the avatar card", async () => {
    await mountCard("office_offline");
    expect(".o_user_im_status .fa-building").toHaveCount(1);
    expect(".o_user_im_status .fa-building").toHaveClass("text-body");
    expect(".o_user_im_status .fa-question-circle").toHaveCount(0);
});

test("other_online renders on the avatar card", async () => {
    await mountCard("other_online");
    expect(".o_user_im_status .fa-location-dot").toHaveCount(1);
    expect(".o_user_im_status .fa-location-dot").toHaveClass("text-success");
    expect(".o_user_im_status .fa-question-circle").toHaveCount(0);
});

test("other_busy renders on the avatar card", async () => {
    await mountCard("other_busy");
    expect(".o_user_im_status .fa-location-dot").toHaveCount(1);
    expect(".o_user_im_status .fa-location-dot").toHaveClass("text-danger");
    expect(".o_user_im_status .fa-question-circle").toHaveCount(0);
});

test("a plain status still gets mail's own icon", async () => {
    await mountCard("online");
    expect(".o_user_im_status .fa-circle").toHaveClass("text-success");
    expect(".o_user_im_status .fa-house").toHaveCount(0);
});

test("a status another module owns is left to it", async () => {
    await mountCard("leave_offline");
    expect(".o_user_im_status .fa-house").toHaveCount(0);
    expect(".o_user_im_status .fa-building").toHaveCount(0);
    expect(".o_user_im_status .fa-location-dot").toHaveCount(0);
});
