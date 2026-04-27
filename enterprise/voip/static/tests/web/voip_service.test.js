import { describe, expect, test } from "@odoo/hoot";
import { start, startServer } from "@mail/../tests/mail_test_helpers";
import { getService, serverState } from "@web/../tests/web_test_helpers";
import { setupVoipTests } from "@voip/../tests/voip_test_helpers";

describe.current.tags("desktop");
setupVoipTests();

test("“hasValidExternalDeviceNumber” is true when an external device number is configured.", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users.settings"].create({
        external_device_number: "+247-555-183-184",
        user_id: serverState.userId,
    });
    await start();
    const voipService = await getService("voip");
    expect(voipService.hasValidExternalDeviceNumber).toBe(true);
});

test("“hasValidExternalDeviceNumber” is false when no external device number is configured.", async () => {
    await start();
    const voipService = await getService("voip");
    expect(voipService.hasValidExternalDeviceNumber).toBe(false);
});
