import { mockService } from "@web/../tests/web_test_helpers";

/* Mock the website service */
// TODO: Remove this mock when the website service is no longer needed in the tests.

export function mockWebsiteService() {
    mockService("website", () => ({
        currentWebsite: {
            id: 1,
            metadata: {
                lang: "en_US",
            },
            default_lang_id: {
                code: "en_US",
            },
        },
    }));
}
