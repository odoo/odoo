import {
    defineMailModels,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, expect, test } from "@odoo/hoot";

describe.current.tags("desktop", "discuss_call_history");
defineMailModels();

test("duration omits an empty hour component", async () => {
    const pyEnv = await startServer();
    const historyId = pyEnv["discuss.call.history"].create({ duration_hour: 109 / 3600 });
    await start();
    await openFormView("discuss.call.history", historyId, {
        arch: `
            <form>
                <field name="duration_hour" widget="discuss_call_history_duration"/>
            </form>
        `,
    });
    expect(".o_field_discuss_call_history_duration time").toHaveText("1m 49s");
});

test("recording indicators prefer video over audio", async () => {
    const pyEnv = await startServer();
    const historyId = pyEnv["discuss.call.history"].create({
        has_audio: true,
        has_recording: true,
        has_video: true,
    });
    await start();
    await openFormView("discuss.call.history", historyId, {
        arch: `
            <form>
                <field name="has_recording" widget="discuss_call_history_indicators"/>
            </form>
        `,
    });
    expect("[data-icon='movie']").toHaveCount(1);
    expect("[data-icon='volume_up']").toHaveCount(0);
});

test("recording indicators show audio when there is no video", async () => {
    const pyEnv = await startServer();
    const historyId = pyEnv["discuss.call.history"].create({
        has_audio: true,
        has_recording: true,
    });
    await start();
    await openFormView("discuss.call.history", historyId, {
        arch: `
            <form>
                <field name="has_recording" widget="discuss_call_history_indicators"/>
            </form>
        `,
    });
    expect("[data-icon='movie']").toHaveCount(0);
    expect("[data-icon='volume_up']").toHaveCount(1);
});
