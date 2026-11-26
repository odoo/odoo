import { expect, getFixture, mockLocation, test, waitFor } from "@odoo/hoot";
import {
    assignDialogTestEnv,
    contains,
    mockService,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";

import { defineWebsiteModels } from "@website/../tests/builder/website_helpers";
import { OptimizeSEODialog } from "@website/components/dialog/seo";

defineWebsiteModels();

test("broken links are checked with their URL but fixed with their stored href", async () => {
    // The links of the page are resolved against the test document.
    mockLocation.href = document.baseURI;
    const { origin } = window.location;
    // The `href` property of these links (normalized by the browser) differs
    // from their `href` attribute (stored in the record).
    const wrapwrapEl = document.createElement("div");
    wrapwrapEl.id = "wrapwrap";
    const recordEl = document.createElement("div");
    Object.assign(recordEl.dataset, { oeModel: "ir.ui.view", oeId: "1", oeField: "arch" });
    for (const [href, label] of [
        [`${origin}/broken/absolute`, "Absolute"],
        ["broken/relative", "Relative"],
        ["/broken/café", "Encoded"],
    ]) {
        const linkEl = document.createElement("a");
        linkEl.setAttribute("href", href);
        linkEl.textContent = label;
        recordEl.append(linkEl);
    }
    wrapwrapEl.append(recordEl);
    getFixture().append(wrapwrapEl);
    mockService("website", {
        currentWebsite: {
            id: 1,
            metadata: {
                mainObject: { id: 1, model: "ir.ui.view" },
                path: `${origin}/page`,
                lang: "en_US",
            },
        },
        pageDocument: document,
        goToWebsite: () => {},
    });
    onRpc("/website/get_seo_data", () => ({
        lang: { code: "en_US", name: "English (US)" },
        default_lang_code: "en_US",
        can_edit_seo: true,
        has_social_default_image: false,
    }));
    onRpc("/website/get_languages", () => []);
    onRpc("/website/get_alt_images", () => "[]");
    onRpc("/*broken/*", (request) => {
        expect.step(`check ${new URL(request.url).pathname}`);
        return new Response("", { status: 404 });
    });
    onRpc("ir.ui.view", "write", () => true);
    onRpc("/website/update_broken_links", async (request) => {
        const { params } = await request.json();
        expect.step(`fix ${params.links.map((link) => link.oldLink).join(", ")}`);
        return true;
    });

    assignDialogTestEnv();
    await mountWithCleanup(OptimizeSEODialog, { props: { close: () => {} } });
    await waitFor("input[aria-label='Encoded']");
    expect.verifySteps([
        "check /broken/absolute",
        `check ${new URL("broken/relative", document.baseURI).pathname}`,
        "check /broken/caf%C3%A9",
    ]);

    for (const label of ["Absolute", "Relative", "Encoded"]) {
        await contains(`input[aria-label='${label}'] ~ button[title^='Remove the link']`).click();
    }
    await contains(".modal-footer .btn-primary").click();
    expect.verifySteps([`fix ${origin}/broken/absolute, broken/relative, /broken/café`]);
});
