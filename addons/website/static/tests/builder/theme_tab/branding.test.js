import { defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";
import { after, describe, test, expect } from "@odoo/hoot";
import { animationFrame, queryOne, waitForNone } from "@odoo/hoot-dom";
import { contains, getService, makeServerError, onRpc } from "@web/../tests/web_test_helpers";
import { exampleContent, modifyText, unfoldAllOptionsGroups } from "@html_builder/../tests/helpers";
import { PREVIEW_TITLE_MARK } from "@website/builder/plugins/theme/theme_branding_utils";

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

const PICKED_SRC = /^data:image\//;
const NAME_INPUT = "[data-action-id='setWebsiteName'] input";
const UNDO = ".o_hb_snippets_menu button[data-icon='undo']";
const REDO = ".o_hb_snippets_menu button[data-icon='redo']";
const SAVE = ".o_hb_snippets_top_actions button[data-action='save']";
const DISCARD = ".o_hb_snippets_top_actions button[data-action='cancel']";
const HEADER_LOGO = ":iframe header .navbar-brand.logo span";
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

/**
 * Opens the Theme tab on a website that has a favicon (`faviconCount`).
 */
async function setupBranding({
    header = HEADER_WITH_IMAGE,
    websiteName = "My Website",
    pageTitle = `Home | ${websiteName}`,
    // The title the layout renders in the default_title meta for designers.
    // Null renders the meta without content.
    defaultTitle = pageTitle,
    footer = "",
    // What reading the websites again returns. By default, the initial name.
    fetchWebsites = null,
    faviconCount = () => 1,
    updateBranding = ({ args }) => {
        expect.step(`update_branding ${JSON.stringify(args[1])}`);
        return {
            name: args[1].name || websiteName,
            has_favicon: args[1].favicon !== false,
            errors: {},
        };
    },
} = {}) {
    // The favicon preview changes the test runner tab (window.top): restore it.
    const iconLinks = [...window.top.document.head.querySelectorAll("link[rel*='icon']")];
    const initialHrefs = iconLinks.map((link) => link.href);
    after(() => iconLinks.forEach((link, i) => (link.href = initialHrefs[i])));

    let websiteReads = 0;
    onRpc("website", "web_search_read", () => {
        if (websiteReads++ && fetchWebsites) {
            return fetchWebsites();
        }
        return websiteRecords(websiteName);
    });
    onRpc("website", "search_count", faviconCount);
    onRpc("website", "update_branding", updateBranding);
    // When the selection lands in the text header link, its popover loads a
    // preview of the home page.
    onRpc("/", () => ({}));
    onRpc("/html_editor/link_preview_internal", () => ({}));
    // The test harness gives the picked image the original id 1.
    onRpc("/html_editor/modify_image/1", () => {
        expect.step("modify_image");
        return { original: "/web/image/99-abc/png_logo.webp" };
    });
    // Not stepped, because the page and branding saves run concurrently.
    const viewSaves = [];
    onRpc("ir.ui.view", "save", ({ args }) => {
        viewSaves.push(args[1]);
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
            id: 44,
            name: "svg_logo",
            mimetype: "image/svg+xml",
            image_src: "/web/static/img/logo.svg",
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
        footerContent: footer,
        onIframeLoaded: ({ contentDocument: doc }) => {
            doc.title = pageTitle;
            pageTitle = doc.title;
            const meta = doc.createElement("meta");
            meta.name = "default_title";
            if (defaultTitle !== null) {
                meta.content = defaultTitle;
            }
            doc.head.append(meta);
        },
    });
    // What the editor does with the page title when the page loads.
    getService("title").setParts({ action: pageTitle });
    await contains(".o_hb_snippets_tabs button[data-name=theme]").click();
    await unfoldAllOptionsGroups();
    return {
        ...builder,
        getSavedArchs: () => viewSaves,
    };
}

async function rename(name) {
    await contains(NAME_INPUT).edit(name);
    await animationFrame();
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

async function clickAndAnimate(selector) {
    await contains(selector).click();
    await animationFrame();
}

async function saveAndClose() {
    await contains(SAVE).click();
    await animationFrame();
}

describe("Website name", () => {
    test("a rename is previewed in the tab title, follows undo/redo, and saves the last name", async () => {
        const { getEditor, getSavedArchs } = await setupBranding({
            fetchWebsites: () => {
                expect.step("fetch websites");
                return websiteRecords("New Name");
            },
        });

        await rename("");
        expect(NAME_INPUT).toHaveValue("My Website");
        await rename("My Website ");
        expect(document.title).toBe("Home | My Website");
        expect(UNDO).not.toBeEnabled();

        await rename("Other Name");
        await rename("New Name");
        expect(document.title).toBe(`Home | New Name${PREVIEW_TITLE_MARK}`);
        expect(HEADER_LOGO).toHaveAttribute("title", "My Website");
        expect(HEADER_LOGO).toHaveAttribute("aria-label", "Logo of My Website");

        await clickAndAnimate(UNDO);
        await clickAndAnimate(UNDO);
        expect(NAME_INPUT).toHaveValue("My Website");
        expect(document.title).toBe("Home | My Website");
        await clickAndAnimate(REDO);
        await clickAndAnimate(REDO);
        expect(NAME_INPUT).toHaveValue("New Name");
        expect(document.title).toBe(`Home | New Name${PREVIEW_TITLE_MARK}`);

        await getEditor().shared.savePlugin.save();
        expect.verifySteps([`update_branding {"name":"New Name"}`, "fetch websites"]);
        expect(getSavedArchs()).toEqual([]);
        // Some saves reload the editor, whose branding plugin reads the name
        // from the website service.
        expect(getService("website").currentWebsite.name).toBe("New Name");

        // Chrome may keep a stale tab label when the title is set to the value
        // it already has. After the save, the page reload sets "Home | New
        // Name" again, so the previewed title must differ from it by an
        // invisible mark.
        expect(document.title).toBe(`Home | New Name${PREVIEW_TITLE_MARK}`);
        await rename("My Website");
        expect(document.title).toBe("Home | My Website");
    });

    test("a page with a custom SEO title is not previewed, the name is still saved", async () => {
        // The page has its own SEO title, which ends with the name by chance:
        // a rename won't change it.
        await setupBranding({
            pageTitle: "Coffee by My Website",
            defaultTitle: "Home | My Website",
        });

        await rename("New Name");
        expect(document.title).toBe("Coffee by My Website");

        await clickAndAnimate(UNDO);
        expect(NAME_INPUT).toHaveValue("My Website");
        await clickAndAnimate(REDO);
        expect(NAME_INPUT).toHaveValue("New Name");

        await saveAndClose();
        expect.verifySteps([`update_branding {"name":"New Name"}`]);
        // The title gets no invisible mark either, so it won't change on reload.
        expect(document.title).toBe("Coffee by My Website");
    });
});

describe("Favicon", () => {
    test("a picked or removed favicon is previewed, follows undo, and Discard puts back every tab icon link", async () => {
        // The tab has an extra icon link (apple-touch-icon), which the
        // editor itself doesn't reset when it closes.
        const appleIcon = window.top.document.createElement("link");
        appleIcon.rel = "apple-touch-icon";
        appleIcon.href = "/apple-touch.png";
        window.top.document.head.appendChild(appleIcon);
        after(() => appleIcon.remove());
        await setupBranding();
        // The test harness shows the same placeholder in every <img>: check the
        // tab icon (window.top) instead.
        const tabIcon = window.top.document.head.querySelector("link[rel*='icon']");
        const initialHref = tabIcon.href;
        const initialAppleHref = appleIcon.href;
        expect(FAVICON_THUMBNAIL).toHaveClass("object-fit-contain");

        // The server crops a PNG favicon to a centered square.
        await pickFavicon("png_logo");
        expect(tabIcon.href).toMatch(PICKED_SRC);
        expect(FAVICON_THUMBNAIL).toHaveClass("object-fit-cover");
        await pickFavicon("svg_logo");
        expect(FAVICON_THUMBNAIL).toHaveClass("object-fit-contain");
        await pickFavicon("remote_logo");
        expect(".o_notification").toHaveText(
            "This image could not be downloaded from its URL. Please upload the file instead."
        );

        await clickAndAnimate(UNDO);
        await clickAndAnimate(UNDO);
        expect(tabIcon.href).toBe(initialHref);
        expect(UNDO).not.toBeEnabled();

        await clickAndAnimate(REMOVE_FAVICON);
        expect(tabIcon.href).toMatch(/\/web\/static\/img\/placeholder\.png$/);
        expect(appleIcon.href).toMatch(/\/web\/static\/img\/placeholder\.png$/);
        expect(FAVICON_THUMBNAIL).toHaveCount(0);
        expect(REMOVE_FAVICON).toHaveCount(0);
        expect(REPLACE_FAVICON).toHaveText("None");

        await contains(DISCARD).click();
        await contains(".modal-footer .btn-primary").click();
        await animationFrame();
        expect(tabIcon.href).toBe(initialHref);
        expect(appleIcon.href).toBe(initialAppleHref);
    });

    test("a website without a favicon shows None", async () => {
        await setupBranding({ faviconCount: () => 0 });
        expect(REPLACE_FAVICON).toHaveText("None");
        expect(FAVICON_THUMBNAIL).toHaveCount(0);
        expect(REMOVE_FAVICON).toHaveCount(0);
    });

    test("the Theme tab waits for the favicon check, which runs again on the next opening when it fails", async () => {
        expect.errors(1);
        const secondCheck = Promise.withResolvers();
        let checks = 0;
        await setupBranding({
            faviconCount: () => {
                if (!checks++) {
                    throw makeServerError({ message: "Server unreachable" });
                }
                return secondCheck.promise;
            },
        });
        expect.verifyErrors(["Server unreachable"]);
        expect(REPLACE_FAVICON).toHaveCount(0);
        expect("button[data-name=theme]").not.toHaveClass("active");
        expect(SAVE).toHaveCount(1);

        // Clicking Theme again does nothing: the builder already counts it as
        // the active tab.
        await contains("button[data-name=theme]").click();
        expect(checks).toBe(1);

        await contains("button[data-name=blocks]").click();
        await contains("button[data-name=theme]").click();
        expect(checks).toBe(2);
        expect(NAME_INPUT).toHaveCount(0);

        secondCheck.resolve(1);
        await animationFrame();
        await unfoldAllOptionsGroups();
        expect(NAME_INPUT).toHaveCount(1);
        expect(REMOVE_FAVICON).toHaveCount(1);
    });
});

describe("Logo", () => {
    test("with a header logo image, undo/redo apply to every logo and the page save writes the logo without an RPC", async () => {
        const { getSavedArchs } = await setupBranding({ footer: FOOTER_WITH_LOGO });
        await pickLogo();
        expect(HEADER_IMG).toHaveAttribute("src", PICKED_SRC);
        expect(FOOTER_IMG).toHaveAttribute("src", PICKED_SRC);

        await clickAndAnimate(UNDO);
        expect(HEADER_IMG).toHaveAttribute("src", LOGO_SRC);
        expect(FOOTER_IMG).toHaveAttribute("src", LOGO_SRC);

        await clickAndAnimate(REDO);
        expect(HEADER_IMG).toHaveAttribute("src", PICKED_SRC);
        await saveAndClose();
        expect.verifySteps(["modify_image", "modify_image"]); // Header and footer.
        expect(getSavedArchs().length).toBe(2);
        expect(getSavedArchs().join("")).not.toInclude("data:");
    });

    test("with a text header, the RPC saves the logo field, and nothing once the pick is undone", async () => {
        // The RPC is the only way the logo is saved, so undo must unstage it too.
        const { getEditor, getSavedArchs } = await setupBranding({
            header: HEADER_WITH_TEXT,
            footer: FOOTER_WITH_LOGO,
        });

        await pickLogo();
        expect(FOOTER_IMG).toHaveAttribute("src", PICKED_SRC);
        await clickAndAnimate(UNDO);
        expect(FOOTER_IMG).toHaveAttribute("src", LOGO_SRC);
        await getEditor().shared.savePlugin.save();
        expect.verifySteps([]);
        expect(getSavedArchs()).toEqual([]);

        await pickLogo();
        expect(FOOTER_IMG).toHaveAttribute("src", PICKED_SRC);
        await getEditor().shared.savePlugin.save();
        expect.verifySteps(["modify_image", `update_branding {"logo":42}`]);
    });
});

describe("Save", () => {
    test("after a save, nothing is staged and the saved values are the new ones", async () => {
        // A text header: the logo is saved by the RPC.
        const { getEditor } = await setupBranding({
            header: HEADER_WITH_TEXT,
            footer: FOOTER_WITH_LOGO,
        });
        const tabIcon = window.top.document.head.querySelector("link[rel*='icon']");

        await rename("New Name");
        expect(":iframe header .navbar-brand").toHaveText("My Website");
        await pickFavicon();
        await pickLogo();

        // Without closing, as before a reload of the editor.
        await getEditor().shared.savePlugin.save();
        expect.verifySteps([
            "modify_image",
            `update_branding {"name":"New Name","favicon":42,"logo":42}`,
        ]);
        await getEditor().shared.savePlugin.save();
        expect.verifySteps([]);

        // The new name is now the saved one, so an empty input falls back to it.
        expect(NAME_INPUT).toHaveValue("New Name");
        expect(document.title).toBe(`Home | New Name${PREVIEW_TITLE_MARK}`);
        await rename("");
        expect(NAME_INPUT).toHaveValue("New Name");
        await getEditor().shared.savePlugin.save();
        expect.verifySteps([]);

        await rename("Third Name");
        expect(document.title).toBe(`Home | Third Name${PREVIEW_TITLE_MARK}`);
        await clickAndAnimate(REMOVE_FAVICON);
        await getEditor().shared.savePlugin.save();
        expect.verifySteps([`update_branding {"name":"Third Name","favicon":false}`]);
        expect(REPLACE_FAVICON).toHaveText("None");

        getEditor().destroy();
        expect(tabIcon.href).toMatch(/\/web\/static\/img\/placeholder\.png$/);
    });

    test("a refused field is dropped with a notification, the rest is saved", async () => {
        const { getEditor, getEditableContent, getSavedArchs } = await setupBranding({
            updateBranding: ({ args }) => {
                expect.step(`update_branding ${JSON.stringify(args[1])}`);
                return {
                    name: "New Name",
                    has_favicon: true,
                    errors: { favicon: "The selected file must be an image." },
                };
            },
            fetchWebsites: () => {
                throw makeServerError({ message: "Server unreachable" });
            },
        });

        await modifyText(getEditor(), getEditableContent());
        await rename("New Name");
        await clickAndAnimate(REMOVE_FAVICON);

        await getEditor().shared.savePlugin.save();
        await animationFrame();
        expect.verifySteps([`update_branding {"name":"New Name","favicon":false}`]);
        expect(getSavedArchs().length).toBe(1);
        expect(".o_notification").toHaveCount(1);
        expect(".o_notification").toHaveText(
            "The favicon could not be saved: The selected file must be an image."
        );
        expect(".o_error_dialog").toHaveCount(0);

        expect(NAME_INPUT).toHaveValue("New Name");
        expect(REMOVE_FAVICON).toHaveCount(1);
    });

    test("after a failed branding call, the page is saved and the saved values are shown again", async () => {
        const { getEditor, getEditableContent, getSavedArchs } = await setupBranding({
            updateBranding: () => {
                expect.step("update_branding");
                throw makeServerError({ message: "Access denied", type: "AccessError" });
            },
        });
        const tabIcon = window.top.document.head.querySelector("link[rel*='icon']");
        const initialHref = tabIcon.href;

        await modifyText(getEditor(), getEditableContent());
        await rename("New Name");
        await clickAndAnimate(REMOVE_FAVICON);

        await getEditor().shared.savePlugin.save();
        await animationFrame();
        expect.verifySteps(["update_branding"]);
        expect(getSavedArchs().length).toBe(1);
        expect(".o_notification").toHaveText(
            "The website branding could not be saved: Access denied"
        );
        expect(".o_error_dialog").toHaveCount(0);

        expect(document.title).toBe("Home | My Website");
        expect(NAME_INPUT).toHaveValue("My Website");
        expect(tabIcon.href).toBe(initialHref);
        expect(REMOVE_FAVICON).toHaveCount(1);

        await getEditor().shared.savePlugin.save();
        expect.verifySteps([]);
    });

    test("saving a custom snippet neither saves the branding nor drops its preview", async () => {
        onRpc("ir.ui.view", "save_snippet", () => {
            expect.step("save_snippet");
            return "Custom Cover";
        });
        await setupBranding();

        queryOne(":iframe #wrap").insertAdjacentHTML(
            "beforeend",
            `<section data-snippet="s_cover" class="s_cover"><p>Cover</p></section>`
        );
        await rename("New Name");

        await contains(":iframe section.s_cover").click();
        await contains("button.oe_snippet_save").click();
        await expect.waitForSteps(["save_snippet"]);
        expect(document.title).toBe(`Home | New Name${PREVIEW_TITLE_MARK}`);
    });
});
