import { describe, test, expect } from "@odoo/hoot";
import { defineWebsiteModels, setupWebsiteBuilderWithSnippet } from "../website_helpers";
import { contains, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { GoogleMapsOptionPlugin } from "@html_builder/website_builder/plugins/options/google_maps_option/google_maps_option_plugin";
import { GoogleMapsOption } from "@html_builder/website_builder/plugins/options/google_maps_option/google_maps_option";
import { queryOne, waitFor, waitForNone } from "@odoo/hoot-dom";

defineWebsiteModels();

describe("API key validation", () => {
    /**
     * - No billing or invalid key: returns 403.
     * - Billing + No API: returns 403.
     * - Billing + Places + Javascript: returns 403.
     *      -> Should not be able to validate the key from editor panel.
     *      -> If key added via backend, adding a map snippet later will open
     *         the key config panel automatically.
     *      -> If clicking on existing map, should open the API key dialog.
     * - Billing + Static + Javascript: return 200.
     *      -> Should still wrongly allow to save the key configuration but it
     *         should reopen immediately.
     * - Billing + Static + Javascript + Places: return 200.
     *      -> Should work.
     *
     * Notes:
     * - Google errors triggered while there no misconfig should not open
     *   any notification or dialog.
     * - There might be some weird behavior when saving multiple considered
     *   valid key during the same edition (which is an acceptable trade-off in
     *   real life).
     */

    /**
     * Stringify an API configuration so it can be used as a bogus API key that
     * is descriptive of what the API key is supposed to give access to.
     */
    const makeKey = (
        config = { billing: false, staticApi: false, placesApi: false, javascriptApi: false }
    ) => JSON.stringify(config);

    const setupGoogleMapsSnippetWithKey = async (key, isFakeValidKey = false) => {
        onRpc("/website/google_maps_api_key", async () =>
            JSON.stringify({
                google_maps_api_key: key,
            })
        );
        patchWithCleanup(GoogleMapsOption.prototype, {
            // Can't do anything since we're not loading the API.
            initializeAutocomplete() {},
        });
        patchWithCleanup(GoogleMapsOptionPlugin.prototype, {
            /**
             * Return the key again instead of actually loading the API, which
             * wouldn't work given we don't have a real key.
             */
            async loadGoogleMapsAPIFromService() {
                window.google = {
                    maps: { places: {} },
                };
                return key;
            },
            /**
             * Mock a fetch call to the Google Maps API supposed to return a
             * status code informing us of whether an API key is valid or not
             * for our purposes.
             */
            fetchGoogleMaps(key) {
                const { billing, staticApi, javascriptApi, placesApi } = JSON.parse(key);
                return {
                    status: billing && staticApi && javascriptApi ? 200 : 403,
                    billing,
                    staticApi,
                    javascriptApi,
                    placesApi,
                };
            },
            /**
             * Mock a successful call to Google Maps' nearby search returning a
             * place so we don't need a valid API key.
             * OR, mock a failed call to Google Maps' nearby search calling the
             * error handler.
             */
            async nearbySearch() {
                if (isFakeValidKey) {
                    return { error: "CRITICAL" };
                } else {
                    return {
                        formatted_address:
                            "9 Rue des Bourlottes, 1367 Grand-Rosière-Hottomont, Belgium",
                        geometry: {
                            location: {
                                lat: () => "50.62994",
                                lng: () => "4.86374",
                            },
                        },
                    };
                }
            },
        });
        await setupWebsiteBuilderWithSnippet("s_google_map");
        if (isFakeValidKey) {
            await waitForNone(":iframe .s_google_map"); // It was removed.
        } else {
            await contains(":iframe .s_google_map").click();
        }
    };
    const keyShouldTriggerDialog = async (config, isFakeValidKey = false) => {
        const key = makeKey(config);
        await setupGoogleMapsSnippetWithKey(key, isFakeValidKey);
        if (isFakeValidKey) {
            // An error should appear since nearbySearch failed.
            await waitFor(".o_notification_manager div[role=alert]");
        }
        const apiKeyInput = await queryOne(".modal-dialog #api_key_input");
        expect(apiKeyInput.value).toBe(key);
        if (!isFakeValidKey) {
            await waitFor(".modal-dialog #api_key_help.text-danger");
        }
    };

    test("having an API key with no billing or API should trigger the opening of the API key dialog", async () => {
        await keyShouldTriggerDialog(); // invalid key (has nothing)
    });

    test("having an API key with no billing should trigger the opening of the API key dialog", async () => {
        await keyShouldTriggerDialog({ staticApi: true, javascriptApi: true, placesApi: true });
    });

    test("having an API key with no static API should trigger the opening of the API key dialog", async () => {
        await keyShouldTriggerDialog({ billing: true, javascriptApi: true, placesApi: true });
    });

    test("having an API key with billing, static API, javascript API and places API should not trigger the opening of the API key dialog", async () => {
        const key = makeKey({
            billing: true,
            staticApi: true,
            javascriptApi: true,
            placesApi: true,
        });
        await setupGoogleMapsSnippetWithKey(key);
        await waitForNone(".modal-dialog #api_key_input");
        await contains(":iframe .s_google_map").click();
    });

    test("having an API key with billing, static API and javascript API but no places API should trigger the opening of the API key dialog even though the response is 200", async () => {
        await keyShouldTriggerDialog(
            { billing: true, staticApi: true, javascriptApi: true, placesApi: false },
            true
        );
    });
});
