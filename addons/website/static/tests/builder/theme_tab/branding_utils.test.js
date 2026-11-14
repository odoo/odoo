import {
    PREVIEW_TITLE_MARK,
    applyLogo,
    createFaviconPreview,
    createTitlePreview,
} from "@website/builder/plugins/theme/theme_branding_utils";
import { describe, expect, test } from "@odoo/hoot";

describe("Theme branding utils", () => {
    test("applyLogo copies the picked image to the header and footer logos only, without the old edits", () => {
        const container = document.createElement("div");
        container.innerHTML = `
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
        // Like an SVG, the picked image has no attributes to overwrite the old ones.
        const picked = document.createElement("img");
        picked.setAttribute("src", "data:image/webp;base64,AAAA");
        picked.className = "o_modified_image_to_save";
        picked.dataset.attachmentId = "43";

        applyLogo(container, picked);
        for (const img of container.querySelectorAll("header img, footer img")) {
            expect(img.getAttribute("src")).toBe("data:image/webp;base64,AAAA");
            expect(img).toHaveClass("o_modified_image_to_save");
            expect(img.dataset.attachmentId).toBe("43");
        }
        const footerImg = container.querySelector("footer img");
        expect(footerImg.dataset.shape).toBe(undefined);
        expect(footerImg.dataset.originalId).toBe(undefined);
        expect(footerImg.getAttribute("style")).toBe("width: 40px; margin: 4px;");
        expect(container.querySelector(".untouched").getAttribute("src")).toBe("ignore.png");
    });

    describe("createTitlePreview", () => {
        function mockTitlePlugin(parts) {
            let currentParts = { ...parts };
            return {
                getParts: () => ({ ...currentParts }),
                setParts: (parts) => {
                    currentParts = { ...currentParts, ...parts };
                },
            };
        }

        // The test runner mocks `document.title`, so a real document can't be used.
        function mockPage(title, defaultTitle = title) {
            return {
                title,
                querySelector: (selector) =>
                    selector === "meta[name='default_title']" ? { content: defaultTitle } : null,
            };
        }

        test("previews the new name at the end of the page title, with an invisible mark until it is back to the original", () => {
            // The homepage title can be the bare name (no page name before it).
            const bareTitle = mockTitlePlugin({ action: "Shop" });
            createTitlePreview(bareTitle, mockPage("Shop")).show("Store", "Shop");
            expect(bareTitle.getParts().action).toBe(`Store${PREVIEW_TITLE_MARK}`);

            const titlePlugin = mockTitlePlugin({ action: "Home | My Website" });
            const preview = createTitlePreview(titlePlugin, mockPage("Home | My Website"));
            preview.show("Store", "My  Website");
            expect(titlePlugin.getParts().action).toBe(`Home | Store${PREVIEW_TITLE_MARK}`);
            // The name is found before the mark.
            preview.show("Market", "Store");
            expect(titlePlugin.getParts().action).toBe(`Home | Market${PREVIEW_TITLE_MARK}`);
            preview.show("My  Website", "Market");
            expect(titlePlugin.getParts().action).toBe("Home | My Website");
        });

        test("leaves a page that doesn't show its default title alone", () => {
            for (const page of [
                mockPage("Coffee by Shop", "Home | Shop"),
                // Pages whose controller sets the title have no default title.
                mockPage("Home | Shop", ""),
            ]) {
                const titlePlugin = mockTitlePlugin({ action: page.title });
                createTitlePreview(titlePlugin, page).show("Store", "Shop");
                expect(titlePlugin.getParts().action).toBe(page.title);
            }
        });
    });

    test("createFaviconPreview puts each link back even if an icon link was added after it was created", () => {
        // A detached document, so the test runner tab favicon is not touched.
        const mockDoc = document.implementation.createHTMLDocument("Mocked Doc");
        const addIconLink = (href) => {
            const link = mockDoc.createElement("link");
            link.rel = "icon";
            link.href = href;
            mockDoc.head.prepend(link);
            return link;
        };
        const iconLink = addIconLink("/icon.ico");
        const preview = createFaviconPreview(mockDoc);
        const addedLink = addIconLink("/added.ico");

        // Each link gets its own href back, not the one of the link that was
        // at its position before.
        preview.show("/new.ico");
        preview.reset();
        expect(addedLink.getAttribute("href")).toBe("/added.ico");
        expect(iconLink.getAttribute("href")).toBe("/icon.ico");
    });
});
