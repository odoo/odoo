import { start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, test, waitFor } from "@odoo/hoot";
import { definePhoneValidationModels } from "@phone_validation/../tests/phone_validation_test_helpers";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { Avatar } from "@mail/views/web/fields/avatar/avatar";

describe.current.tags("desktop");
definePhoneValidationModels();

async function openPartnerCard(values) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Jane", ...values });
    await start();
    await mountWithCleanup(Avatar, { props: { resId: partnerId, resModel: "res.partner" } });
    await contains(".o-mail-Avatar img").click();
}

test("Avatar card shows the formatted phone number first", async () => {
    await openPartnerCard({
        phone: "0470 00 00 00",
        phone_sanitized: "+32470000000",
        phone_formatted: "+32 470 00 00 00",
    });
    await waitFor(".o-mail-avatar-card-tel:text('+32 470 00 00 00')");
});

test("Avatar card falls back to the sanitized phone number", async () => {
    await openPartnerCard({ phone: "0470 00 00 00", phone_sanitized: "+32470000000" });
    await waitFor(".o-mail-avatar-card-tel:text('+32470000000')");
});

test("Avatar card falls back to the phone number", async () => {
    await openPartnerCard({ phone: "0470 00 00 00" });
    await waitFor(".o-mail-avatar-card-tel:text('0470 00 00 00')");
});
