import { defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";
import { after, describe, test, expect } from "@odoo/hoot";
import { animationFrame, queryAllTexts, waitForNone } from "@odoo/hoot-dom";
import { contains, makeServerError, onRpc } from "@web/../tests/web_test_helpers";
import { exampleContent, unfoldAllOptionsGroups } from "@html_builder/../tests/helpers";

defineWebsiteModels();

const LOGO_SRC = "/web/image/website/1/logo";
const HEADER_WITH_IMAGE = `
    <header id="top" data-oe-model="ir.ui.view" data-oe-id="2" data-oe-field="arch">
        <nav><a href="/" class="navbar-brand logo">
            <span data-oe-model="website" data-oe-id="1" data-oe-field="logo" data-oe-type="image"
                data-oe-expression="website.logo" role="img"
                aria-label="Logo of My Website" title="My Website"><img src="${LOGO_SRC}" alt="My Website"/></span>
        </a></nav>
    </header>`;
const FOOTER_WITH_LOGO = `
    <footer id="bottom" data-oe-model="ir.ui.view" data-oe-id="3" data-oe-field="arch">
        <div class="o_footer_logo">
            <img src="${LOGO_SRC}" alt="My Website" data-shape="geo_square" style="height: 20px; width: 40px;"/>
        </div>
        <img class="other_image" src="${LOGO_SRC}"/>
    </footer>`;
const BRANDING_WITH_FAVICON = `<div id="o_website_branding" class="d-none" data-website-name="My Website" data-saved-name="My Website" data-favicon-src="/web/image/website/1/favicon?unique=1"></div>`;

const PICKED_SRC = /^data:image\//;
const NAME_INPUT = "[data-label='Name'] input";
const UNDO = ".o_hb_snippets_menu button[data-icon='undo']";
const REDO = ".o_hb_snippets_menu button[data-icon='redo']";
const HEADER_IMG = ":iframe header .navbar-brand.logo img";
const FOOTER_IMG = ":iframe footer .o_footer_logo img";
const REPLACE_FAVICON = "[data-action-id='replaceBrandingImage'][data-action-param='favicon']";
const REMOVE_FAVICON = "[data-action-id='removeFavicon']";
const FAVICON_THUMBNAIL = "[data-label='Favicon'] img";

async function setupBranding({
    header = HEADER_WITH_IMAGE,
    footer = "",
    pageTitle = "Home | My Website",
    updateBranding = () => ({}),
} = {}) {
    onRpc("website", "update_branding", ({ args }) => {
        expect.step(`update_branding ${JSON.stringify(args[1])}`);
        return updateBranding();
    });
    onRpc("/", () => ({}));
    onRpc("/html_editor/link_preview_internal", () => ({}));
    onRpc("ir.ui.view", "save", ({ args }) => {
        expect.step(`ir.ui.view save ${args[0]}`);
        return true;
    });
    onRpc("ir.attachment", "search_read", () => [
        {
            id: 42,
            name: "png_logo",
            mimetype: "image/png",
            image_src: "/web/static/img/logo2.png",
            type: "binary",
            access_token: false,
            public: true,
        },
    ]);
    // Mock the tab's favicon and title: the branding preview changes them
    const iconEl = document.createElement("link");
    iconEl.rel = "icon";
    iconEl.href = "/saved_favicon.ico";
    document.head.prepend(iconEl);
    after(() => iconEl.remove());
    const builder = await setupWebsiteBuilder(exampleContent, {
        headerContent: header,
        footerContent: footer + BRANDING_WITH_FAVICON,
        onIframeLoaded: (iframeEl) => {
            const iframeDoc = iframeEl.contentDocument;
            iframeDoc.title = pageTitle;
            const metaEl = iframeDoc.createElement("meta");
            metaEl.name = "default_title";
            metaEl.content = "Home | My Website";
            iframeDoc.head.append(metaEl);
        },
    });
    await contains(".o_hb_snippets_tabs button[data-name=theme]").click();
    await unfoldAllOptionsGroups();
    return { ...builder, iconEl };
}

async function pickImage(field) {
    await contains(`[data-action-id='replaceBrandingImage'][data-action-param='${field}']`).click();
    await contains(".o_select_media_dialog .o_button_area[aria-label='png_logo']").click();
    await waitForNone(".o_select_media_dialog");
}

test("a refused field or a failed call shows a notification, the other fields are saved", async () => {
    let callFails = false;
    const { getEditor } = await setupBranding({
        updateBranding: () => {
            if (callFails) {
                throw makeServerError({ message: "Server unreachable" });
            }
            return { favicon: "The image could not be downloaded from its URL." };
        },
    });
    onRpc("website", "web_search_read", () => {
        expect.step("fetch websites");
        throw makeServerError({ message: "Server unreachable" });
    });

    await contains(NAME_INPUT).edit("New Name");
    await pickImage("favicon");
    await getEditor().shared.savePlugin.save();
    await animationFrame();
    expect.verifySteps([`update_branding {"name":"New Name","favicon":42}`, "fetch websites"]);
    expect(queryAllTexts(".o_notification")).toEqual([
        "The favicon could not be saved: The image could not be downloaded from its URL.",
    ]);

    callFails = true;
    await contains(NAME_INPUT).edit("Other Name");
    await getEditor().shared.savePlugin.save();
    await animationFrame();
    expect.verifySteps([`update_branding {"name":"Other Name","favicon":42}`]);
    expect(queryAllTexts(".o_notification")).toEqual([
        "The favicon could not be saved: The image could not be downloaded from its URL.",
        "The website branding could not be saved: Server unreachable",
    ]);
});

describe("Preview", () => {
    test("the tab previews the name and follows history", async () => {
        await setupBranding();

        await contains(NAME_INPUT).edit("");
        expect(NAME_INPUT).toHaveValue("My Website");

        await contains(NAME_INPUT).edit("New  Name");
        expect(document.title).toBe("Home | New Name\u200b");

        await contains(UNDO).click();
        expect(document.title).toBe("Home | My Website");
        expect(NAME_INPUT).toHaveValue("My Website");
        expect(UNDO).toHaveAttribute("disabled");

        await contains(REDO).click();
        expect(document.title).toBe("Home | New Name\u200b");
    });

    test("the tab previews the favicon and follows history", async () => {
        const { getEditor, iconEl } = await setupBranding();
        expect(FAVICON_THUMBNAIL).toHaveAttribute(
            "data-src",
            "/web/image/website/1/favicon?unique=1"
        );

        await contains(REMOVE_FAVICON).click();
        expect(REPLACE_FAVICON).toHaveText("None");
        expect(iconEl).toHaveAttribute("href", "/web/static/img/placeholder.png");

        await contains(UNDO).click();
        expect(iconEl).toHaveAttribute("href", /\/saved_favicon\.ico$/);

        await pickImage("favicon");
        expect(FAVICON_THUMBNAIL).toHaveAttribute("data-src", "/web/image/42");
        expect(iconEl).toHaveAttribute("href", "/web/image/42");

        getEditor().destroy();
        expect(iconEl).toHaveAttribute("href", /\/saved_favicon\.ico$/);
    });

    test("a page with its own SEO title keeps it in the tab", async () => {
        await setupBranding({ pageTitle: "Offers at My Website" });

        await contains(NAME_INPUT).edit("New Name");
        expect(document.title).not.toInclude("New Name");
    });

    test("a picked logo replaces the header and footer logos only, without their old edits, and follows history", async () => {
        await setupBranding({ footer: FOOTER_WITH_LOGO });

        await pickImage("logo");
        for (const selector of [HEADER_IMG, FOOTER_IMG]) {
            expect(selector).toHaveAttribute("src", PICKED_SRC);
            expect(selector).toHaveClass("o_modified_image_to_save");
        }
        expect(FOOTER_IMG).not.toHaveAttribute("data-shape");
        expect(FOOTER_IMG).toHaveAttribute("style", "width: 40px;");
        expect(":iframe footer .other_image").toHaveAttribute("src", LOGO_SRC);

        await contains(UNDO).click();
        expect(HEADER_IMG).toHaveAttribute("src", LOGO_SRC);
        expect(FOOTER_IMG).toHaveAttribute("src", LOGO_SRC);
        expect(FOOTER_IMG).toHaveAttribute("data-shape", "geo_square");
        expect(FOOTER_IMG).toHaveAttribute("style", "height: 20px; width: 40px;");
        expect(UNDO).toHaveAttribute("disabled");

        await contains(REDO).click();
        expect(HEADER_IMG).toHaveAttribute("src", PICKED_SRC);
        expect(FOOTER_IMG).toHaveAttribute("src", PICKED_SRC);
        expect(FOOTER_IMG).not.toHaveAttribute("data-shape");
    });
});

describe("Logo RPC depending on the header", () => {
    test("with a header logo image, the logo is not sent", async () => {
        const { getEditor } = await setupBranding();

        await pickImage("logo");
        await getEditor().shared.savePlugin.save();
        expect.verifySteps(["ir.ui.view save 1"]);
    });

    test("without a header logo image, the logo is sent", async () => {
        const { getEditor } = await setupBranding({ header: "" });

        await pickImage("logo");
        await getEditor().shared.savePlugin.save();
        expect.verifySteps([`update_branding {"logo":42}`]);
    });
});
