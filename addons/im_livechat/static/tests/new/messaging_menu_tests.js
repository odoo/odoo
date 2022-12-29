/** @odoo-module */

import { getFixture } from "@web/../tests/helpers/utils";

import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { click, start, startServer } from "@mail/../tests/helpers/test_utils";

let target;
QUnit.module("mobile messaging menu", {
    beforeEach() {
        target = getFixture();
        patchUiSize({ size: SIZES.SM });
    },
});

QUnit.test(
    "Livechat button is not present when there is no livechat thread",
    async function (assert) {
        await start();
        await click(".o_menu_systray i[aria-label='Messages']");
        assert.containsOnce(target, ".o-mail-messaging-menu");
        assert.containsNone(target, ".o-mail-messaging-menu-navbar:contains(Livechat)");
    }
);

QUnit.test(
    "Livechat button is present when there is at least one livechat thread",
    async function (assert) {
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
        assert.containsOnce(target, ".o-mail-messaging-menu");
        assert.containsOnce(target, ".o-mail-messaging-menu-navbar:contains(Livechat)");
    }
);
