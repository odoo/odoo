import { defineMailModels, start } from "@mail/../tests/mail_test_helpers";
import { describe, test, waitFor } from "@odoo/hoot";

describe.current.tags("desktop");
defineMailModels();

test("User menu shows im_status icon", async () => {
    await start();
    await waitFor(".o_user_menu .o-mail-ImStatus");
});
