import { test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { advanceTime, mockDate } from "@odoo/hoot-mock";

import { mockService, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { defineWebsiteModels } from "@website/../tests/builder/website_helpers";
import { PublishSystrayItem } from "@website/client_actions/website_preview/publish_website_systray_item";

defineWebsiteModels();

test("scheduled publication label counts down, then the page shows as published", async () => {
    mockDate("2026-10-13 10:00:00", 0);
    mockService("website", {
        currentWebsite: {
            metadata: {
                isPublished: false,
                mainObject: { id: 1, model: "website.page" },
                publishOn: "2026-10-13 10:01:30",
            },
        },
    });
    await mountWithCleanup(PublishSystrayItem);
    await waitFor(".o_website_publish_container span:text(Published in 1 minute):count(1)");
    await advanceTime(60 * 1000);
    await waitFor(".o_website_publish_container span:text(Published shortly):count(1)");
    await advanceTime(60 * 1000);
    await waitFor(".o_website_publish_container span:text(Published):count(1)");
    await waitFor(".o_website_publish_container input:checked:count(1)");
});
