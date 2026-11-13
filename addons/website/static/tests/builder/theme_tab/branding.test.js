import { applyLogo } from "@website/builder/plugins/theme/theme_branding_plugin";
import { defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";
import { after, describe, test, expect } from "@odoo/hoot";
import { animationFrame, queryAllTexts, waitForNone } from "@odoo/hoot-dom";
import { contains, getService, makeServerError, onRpc } from "@web/../tests/web_test_helpers";
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
const HEADER_WITH_TEXT = `
    <header id="top" data-oe-model="ir.ui.view" data-oe-id="2" data-oe-field="arch">
        <nav><a href="/" class="navbar-brand">My Website</a></nav>
    </header>`;
const FOOTER_WITH_LOGO = `
    <footer id="bottom" data-oe-model="ir.ui.view" data-oe-id="3" data-oe-field="arch">
        <div class="o_footer_logo"><img src="${LOGO_SRC}" alt="My Website"/></div>
    </footer>`;

const HEADER_LOGO_SAVED = "ir.ui.view save 1";
const FOOTER_SAVED = "ir.ui.view save 3";

const SAVED_FAVICON_SRC = "/web/image/website/1/favicon?unique=1";
const BRANDING_WITH_FAVICON = `<div id="o_website_branding" class="d-none" data-website-name="My Website" data-saved-name="My Website" data-favicon-src="${SAVED_FAVICON_SRC}"></div>`;

const PICKED_SRC = /^data:image\//;
const NAME_INPUT = "[data-label='Name'] input";
const UNDO = ".o_hb_snippets_menu button[data-icon='undo']";
const REDO = ".o_hb_snippets_menu button[data-icon='redo']";
const HEADER_IMG = ":iframe header .navbar-brand.logo img";
const FOOTER_IMG = ":iframe footer .o_footer_logo img";
const REPLACE_FAVICON = "[data-action-id='replaceBrandingImage'][data-action-param='favicon']";
const REMOVE_FAVICON = "[data-action-id='removeFavicon']";
const FAVICON_THUMBNAIL = "[data-label='Favicon'] img";
const REPLACE_LOGO =
    "[data-label='Logo'] [data-action-id='replaceBrandingImage'][data-action-param='logo']";

function websiteRecords(name) {
    return {
        length: 1,
        records: [{ id: 1, name, default_lang_id: { code: "en_US" }, company_id: 1 }],
    };
}

async function setupBranding({
    header = HEADER_WITH_IMAGE,
    websiteName = "My Website",
    footer = "",
    branding = BRANDING_WITH_FAVICON,
    pageTitle = { title: "Home | My Website", defaultTitle: "Home | My Website" },
    refetchedWebsites = null,
    updateBranding = ({ args }) => {
        expect.step(`update_branding ${JSON.stringify(args[1])}`);
        return {};
    },
} = {}) {
    let websiteReads = 0;
    onRpc("website", "web_search_read", () => {
        if (websiteReads++ && refetchedWebsites) {
            return refetchedWebsites();
        }
        return websiteRecords(websiteName);
    });
    onRpc("website", "update_branding", updateBranding);
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
        {
            id: 43,
            name: "remote_logo",
            mimetype: "image/png",
            image_src: "/web/static/img/logo.png",
            url: "/web/static/img/logo.png",
            type: "url",
            access_token: false,
            public: true,
        },
    ]);
    const builder = await setupWebsiteBuilder(exampleContent, {
        headerContent: header,
        footerContent: footer + branding,
        onIframeLoaded: (iframeEl) => {
            const iframeDoc = iframeEl.contentDocument;
            iframeDoc.title = pageTitle.title;
            const metaEl = iframeDoc.createElement("meta");
            metaEl.name = "default_title";
            metaEl.content = pageTitle.defaultTitle;
            iframeDoc.head.append(metaEl);
        },
    });
    await contains(".o_hb_snippets_tabs button[data-name=theme]").click();
    await unfoldAllOptionsGroups();
    return builder;
}

async function pickImage(name = "png_logo") {
    await contains(`.o_select_media_dialog .o_button_area[aria-label='${name}']`).click();
    await waitForNone(".o_select_media_dialog");
    await animationFrame();
}

async function pickFavicon(name) {
    await contains(REPLACE_FAVICON).click();
    await pickImage(name);
}

async function pickLogo(name) {
    await contains(REPLACE_LOGO).click();
    await pickImage(name);
}

describe("Website name", () => {
    test("a rename saves the last name", async () => {
        const { getEditor } = await setupBranding({
            refetchedWebsites: () => {
                expect.step("fetch websites");
                return websiteRecords("New Name");
            },
        });

        expect("[data-container-title='Website Identification']").toHaveCount(1);

        await contains(NAME_INPUT).edit("");
        expect(NAME_INPUT).toHaveValue("My Website");
        expect(UNDO).not.toBeEnabled();

        await contains(NAME_INPUT).edit("New Name");
        await getEditor().shared.savePlugin.save();
        expect.verifySteps([`update_branding {"name":"New Name"}`, "fetch websites"]);
        expect(getService("website").currentWebsite.name).toBe("New Name");
    });
});

describe("Favicon", () => {
    test("a picked or removed favicon is shown in the row and saved", async () => {
        const { getEditor } = await setupBranding();
        expect(FAVICON_THUMBNAIL).toHaveAttribute("data-src", SAVED_FAVICON_SRC);

        await pickFavicon("png_logo");
        expect(FAVICON_THUMBNAIL).toHaveAttribute("data-src", "/web/image/42");

        await contains(REMOVE_FAVICON).click();
        expect(FAVICON_THUMBNAIL).toHaveCount(0);
        expect(REMOVE_FAVICON).toHaveCount(0);
        expect(REPLACE_FAVICON).toHaveText("None");

        await getEditor().shared.savePlugin.save();
        expect.verifySteps([`update_branding {"favicon":false}`]);
    });
});

describe("Logo", () => {
    test("a picked logo replaces the header and footer logos only, without their old edits", () => {
        const containerEl = document.createElement("div");
        containerEl.innerHTML = `
            <header>
                <div class="navbar-brand logo">
                    <span><img src="old_header.png" /></span>
                </div>
            </header>
            <footer>
                <div class="o_footer_logo">
                    <img src="old_footer.png" data-shape="html_builder/geometric/geo_square" data-original-id="7"
                        style="transform: rotate(10deg); transform-origin: 0 0; width: 40px; height: 20px; margin: 4px;" />
                </div>
            </footer>
            <div>
                <img class="untouched" src="ignore.png" />
            </div>
        `;
        const pickedEl = document.createElement("img");
        pickedEl.setAttribute("src", "data:image/webp;base64,AAAA");
        pickedEl.className = "o_modified_image_to_save";
        pickedEl.dataset.attachmentId = "43";

        applyLogo(containerEl, pickedEl);
        for (const imgEl of containerEl.querySelectorAll("header img, footer img")) {
            expect(imgEl.getAttribute("src")).toBe("data:image/webp;base64,AAAA");
            expect(imgEl).toHaveClass("o_modified_image_to_save");
            expect(imgEl.dataset.attachmentId).toBe("43");
        }
        const footerImgEl = containerEl.querySelector("footer img");
        expect(footerImgEl.dataset.shape).toBe(undefined);
        expect(footerImgEl.dataset.originalId).toBe(undefined);
        expect(footerImgEl.getAttribute("style")).toBe("width: 40px; margin: 4px;");
        expect(containerEl.querySelector(".untouched").getAttribute("src")).toBe("ignore.png");
    });

    test("with a header logo image, the page save writes the logo without an RPC", async () => {
        const { getEditor } = await setupBranding({ footer: FOOTER_WITH_LOGO });

        await pickLogo();
        expect(HEADER_IMG).toHaveAttribute("src", PICKED_SRC);
        expect(FOOTER_IMG).toHaveAttribute("src", PICKED_SRC);

        await getEditor().shared.savePlugin.save();
        expect.verifySteps([HEADER_LOGO_SAVED, FOOTER_SAVED]);
    });

    test("with a text header, the RPC saves the logo field", async () => {
        const { getEditor } = await setupBranding({
            header: HEADER_WITH_TEXT,
            footer: FOOTER_WITH_LOGO,
        });

        await pickLogo();
        expect(FOOTER_IMG).toHaveAttribute("src", PICKED_SRC);

        await getEditor().shared.savePlugin.save();
        expect.verifySteps([FOOTER_SAVED, `update_branding {"logo":42}`]);
    });
});

describe("Undo/redo", () => {
    test("undo and redo apply to the name, favicon and logo; undone changes are not saved", async () => {
        const { getEditor } = await setupBranding({
            header: HEADER_WITH_TEXT,
            footer: FOOTER_WITH_LOGO,
        });
        await contains(NAME_INPUT).edit("New Name");
        await pickFavicon("png_logo");
        await pickLogo();

        await contains(UNDO).click();
        expect(FOOTER_IMG).toHaveAttribute("src", LOGO_SRC);
        expect(FAVICON_THUMBNAIL).toHaveAttribute("data-src", "/web/image/42");

        await contains(UNDO).click();
        expect(FAVICON_THUMBNAIL).toHaveAttribute("data-src", SAVED_FAVICON_SRC);
        expect(NAME_INPUT).toHaveValue("New Name");

        await contains(UNDO).click();
        expect(NAME_INPUT).toHaveValue("My Website");
        expect(UNDO).not.toBeEnabled();

        await contains(REDO).click();
        expect(NAME_INPUT).toHaveValue("New Name");
        expect(FAVICON_THUMBNAIL).toHaveAttribute("data-src", SAVED_FAVICON_SRC);

        await contains(REDO).click();
        expect(FAVICON_THUMBNAIL).toHaveAttribute("data-src", "/web/image/42");
        expect(FOOTER_IMG).toHaveAttribute("src", LOGO_SRC);

        await contains(REDO).click();
        expect(FOOTER_IMG).toHaveAttribute("src", PICKED_SRC);

        await contains(UNDO).click();
        await contains(UNDO).click();
        await contains(UNDO).click();
        await getEditor().shared.savePlugin.save();
        expect.verifySteps([]);
    });
});

describe("Save", () => {
    test("a saved name with surrounding spaces is not sent again", async () => {
        const { getEditor } = await setupBranding({
            websiteName: " My Website ",
            branding: `<div id="o_website_branding" class="d-none" data-website-name=" My Website " data-saved-name=" My Website "></div>`,
        });

        await getEditor().shared.savePlugin.save();
        expect.verifySteps([]);
    });

    test("a refused field or a failed call shows a notification; the rest is saved even if the refresh fails", async () => {
        let calls = 0;
        const { getEditor } = await setupBranding({
            updateBranding: ({ args }) => {
                expect.step(`update_branding ${JSON.stringify(args[1])}`);
                if (calls++) {
                    throw makeServerError({ message: "Access denied", type: "AccessError" });
                }
                return { favicon: "Invalid branding values." };
            },
            refetchedWebsites: () => {
                expect.step("fetch websites");
                throw makeServerError({ message: "Server unreachable" });
            },
        });

        await contains(NAME_INPUT).edit("New Name");
        await pickFavicon("png_logo");
        await getEditor().shared.savePlugin.save();
        await animationFrame();
        expect.verifySteps([`update_branding {"name":"New Name","favicon":42}`, "fetch websites"]);
        expect(queryAllTexts(".o_notification")).toEqual([
            "The favicon could not be saved: Invalid branding values.",
        ]);

        await contains(NAME_INPUT).edit("Other Name");
        await getEditor().shared.savePlugin.save();
        await animationFrame();
        expect.verifySteps([`update_branding {"name":"Other Name","favicon":42}`]);
        expect(queryAllTexts(".o_notification")).toEqual([
            "The favicon could not be saved: Invalid branding values.",
            "The website branding could not be saved: Access denied",
        ]);
        expect(".o_error_dialog").toHaveCount(0);
    });
});

describe("Browser tab preview", () => {
    test("the tab title shows the edited name, marked until it is the saved one", async () => {
        await setupBranding();

        await contains(NAME_INPUT).edit("New  Name");
        expect(document.title).toBe("Home | New Name\u200b");

        await contains(UNDO).click();
        expect(document.title).toBe("Home | My Website");
    });

    test("a page with its own SEO title keeps it", async () => {
        await setupBranding({
            pageTitle: { title: "Offers at My Website", defaultTitle: "Home | My Website" },
        });

        await contains(NAME_INPUT).edit("New Name");
        expect(document.title).not.toInclude("New Name");
    });

    test("the tab icon shows the picked or removed favicon, and the saved one after undo or leaving", async () => {
        const iconEl = document.createElement("link");
        iconEl.rel = "icon";
        iconEl.href = "/saved_favicon.ico";
        document.head.prepend(iconEl);
        after(() => iconEl.remove());
        const { getEditor } = await setupBranding();

        await pickFavicon("png_logo");
        expect(iconEl).toHaveAttribute("href", "/web/image/42");

        await contains(REMOVE_FAVICON).click();
        expect(iconEl).toHaveAttribute("href", "/web/static/img/placeholder.png");

        await contains(UNDO).click();
        await contains(UNDO).click();
        expect(iconEl).toHaveAttribute("href", /\/saved_favicon\.ico$/);

        await pickFavicon("png_logo");
        getEditor().destroy();
        expect(iconEl).toHaveAttribute("href", /\/saved_favicon\.ico$/);
    });
});
