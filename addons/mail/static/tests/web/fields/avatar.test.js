import { defineMailModels, start } from "@mail/../tests/mail_test_helpers";
import { describe, test, waitFor, waitForNone } from "@odoo/hoot";
import { contains, mountWithCleanup, serverState } from "@web/../tests/web_test_helpers";

import { Avatar } from "@mail/views/web/fields/avatar/avatar";

describe.current.tags("desktop");
defineMailModels();

test("basic rendering", async () => {
    await start();
    await mountWithCleanup(Avatar, {
        props: {
            resId: serverState.userId,
            resModel: "res.users",
            displayName: "User display name",
        },
    });
    await waitFor(".o-mail-Avatar:count(1)");
    await waitFor(".o-mail-Avatar img:count(1)");
    await waitFor(".o-mail-Avatar img[data-src='/web/image/res.users/7/avatar_128']:count(1)");
    await waitFor(".o-mail-Avatar span:count(1)");
    await waitFor(".o-mail-Avatar span:text('User display name'):count(1)");
    await waitForNone(".o_avatar_card");
    await contains(".o-mail-Avatar img:count(1)").click();
    await waitFor(".o_avatar_card:count(1)");
});

test("avatar with uniqueId props", async () => {
    await start();
    await mountWithCleanup(Avatar, {
        props: {
            resId: serverState.userId,
            resModel: "res.users",
            displayName: "User display name",
            uniqueId: 123789,
        },
    });
    await waitFor(
        ".o-mail-Avatar img[data-src='/web/image/res.users/7/avatar_128?unique=123789']:count(1)"
    );
});
