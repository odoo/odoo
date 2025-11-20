import { describe, expect, test } from "@odoo/hoot";
import { contains, defineMailModels, start } from "@mail/../tests/mail_test_helpers";
import { getService } from "@web/../tests/web_test_helpers";
import { MESSAGE_SOUND_LS_19_1 } from "@mail/core/common/upgrade/upgrade_19_1";

describe.current.tags("desktop");
defineMailModels();

test("message sound 'off' from 19.1 is dropped when downgrading to 19.0", async () => {
    localStorage.setItem(MESSAGE_SOUND_LS_19_1, `{"value":false,"version":"19.1"}`);
    await start({ serverVersion: [19, 0] });
    getService("action").doAction({
        tag: "mail.discuss_notification_settings_action",
        type: "ir.actions.client",
    });
    await contains("label:has(h5:contains('Message sound')) input:checked");
    expect(localStorage.getItem(MESSAGE_SOUND_LS_19_1)).toBe(null);
});
