import { describe, expect, test } from "@odoo/hoot";
import {
    defineMailModels,
    patchBrowserNotification,
    start,
} from "@mail/../tests/mail_test_helpers";
import { makeRecordFieldLocalId } from "@mail/model/misc";
import { toRawValue } from "@mail/utils/common/local_storage";
import { Store } from "@mail/model/store";
import { getService } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("'Turn on notification' messaging menu item is dismissed", async () => {
    localStorage.setItem("mail.user_setting.push_notification_dismissed", "true");
    patchBrowserNotification("default");
    const IS_NOTIFICATION_PERMISSION_LS = makeRecordFieldLocalId(
        Store.localId(),
        "isNotificationPermissionDismissed"
    );
    await start();
    expect(getService("mail.store").isNotificationPermissionDismissed).toBe(true);
    expect(localStorage.getItem(IS_NOTIFICATION_PERMISSION_LS)).toBe(toRawValue(true));
    expect(localStorage.getItem("mail.user_setting.push_notification_dismissed")).toBe(null);
});
