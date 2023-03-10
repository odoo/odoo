/** @odoo-module */

import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { click, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("mobile messaging menu", {
    beforeEach() {
        patchUiSize({ size: SIZES.SM });
    },
});

QUnit.test("Livechat button is not present when there is no livechat thread", async (assert) => {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce($, ".o-MessagingMenu");
    assert.containsNone($, ".o-MessagingMenu-navbar:contains(Livechat)");
});

QUnit.test(
    "Livechat button is present when there is at least one livechat thread",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["mail.channel"].create({
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: pyEnv.publicPartnerId }],
            ],
            channel_type: "livechat",
            livechat_operator_id: pyEnv.currentPartnerId,
        });
        await start();
        await click(".o_menu_systray i[aria-label='Messages']");
        assert.containsOnce($, ".o-MessagingMenu");
        assert.containsOnce($, ".o-MessagingMenu-navbar:contains(Livechat)");
    }
);
