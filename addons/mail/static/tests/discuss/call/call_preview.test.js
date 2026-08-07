import { defineMailModels, mockGetMedia, start } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test, waitFor, waitUntil } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { CallPreview } from "@mail/discuss/call/common/call_preview";

describe.current.tags("desktop");
defineMailModels();

test("enabling the camera preview reports the camera state even before the video element mounts", async () => {
    mockGetMedia();
    await start();
    const settings = [];
    await mountWithCleanup(CallPreview, {
        props: {
            activateCamera: 1,
            onSettingsChanged: (s) => settings.push(s),
        },
    });
    // The camera is enabled before its stream is assigned to the <video> element. The parent must
    // still be told the camera is on, otherwise a guest whose camera is on in the preview joins the
    // call with the camera off.
    const video = await waitFor("video:count(1)");
    await waitUntil(() => video.srcObject);
    expect(settings).toEqual([{ camera: true }]);
});
