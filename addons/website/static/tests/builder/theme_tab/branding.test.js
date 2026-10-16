import { defineWebsiteModels } from "../website_helpers";
import {
    replaceLastOccurrence,
    buildMediaUrl,
    applyLogo,
    applyFavicon,
    applyWebsiteName,
} from "@website/builder/plugins/theme/theme_website_identification_util";
import { WebsiteBrandingPlugin } from "@website/builder/plugins/theme/theme_website_identification_plugin";
import { describe, test, expect, beforeEach } from "@odoo/hoot";
import { patch } from "@web/core/utils/patch";

defineWebsiteModels();

describe("Website Branding Helpers", () => {
    describe("replaceLastOccurrence", () => {
        test("replaces only the last occurrence of a string", () => {
            const result = replaceLastOccurrence("Odoo - Odoo", "Odoo", "Test");
            expect(result).toBe("Odoo - Test");
        });

        test("returns the original string if the search term is not found", () => {
            const result = replaceLastOccurrence("Hello World", "Odoo", "Test");
            expect(result).toBe("Hello World");
        });

        test("handles overlapping strings correctly", () => {
            const result = replaceLastOccurrence("aaa", "a", "b");
            expect(result).toBe("aab");
        });
    });

    describe("buildMediaUrl", () => {
        test("returns null if hasMedia is false", () => {
            expect(buildMediaUrl(1, "logo", false, 12345)).toBe(null);
        });
    });
    describe("applyLogo", () => {
        let container;

        // Avant chaque test, on recrée un DOM propre pour éviter les interférences
        beforeEach(() => {
            container = document.createElement("div");
            container.innerHTML = `
                <header>
                    <div class="navbar-brand logo">
                        <span><img src="old_header.png" /></span>
                    </div>
                </header>
                <footer>
                    <div class="o_footer_logo">
                        <img src="old_footer.png" />
                    </div>
                </footer>
                <div>
                    <!-- This image should always remain untouched -->
                    <img class="untouched" src="ignore.png" />
                </div>
            `;
        });

        test("updates all target logos by default", () => {
            applyLogo(container, "new_logo.png");

            const headerLogo = container.querySelector("header .navbar-brand.logo span img");
            expect(headerLogo.getAttribute("src")).toBe("new_logo.png");

            const footerLogo = container.querySelector("footer .o_footer_logo img");
            expect(footerLogo.getAttribute("src")).toBe("new_logo.png");

            const untouchedLogo = container.querySelector(".untouched");
            expect(untouchedLogo.getAttribute("src")).toBe("ignore.png");
        });

        test("only updates the logos specified in the targets array", () => {
            applyLogo(container, "new_logo.png", ["header"]);

            const headerLogo = container.querySelector("header .navbar-brand.logo span img");
            expect(headerLogo.getAttribute("src")).toBe("new_logo.png"); // Mis à jour

            const footerLogo = container.querySelector("footer .o_footer_logo img");
            expect(footerLogo.getAttribute("src")).toBe("old_footer.png"); // Intact

            const untouchedLogo = container.querySelector(".untouched");
            expect(untouchedLogo.getAttribute("src")).toBe("ignore.png"); // Intact
        });
    });

    describe("applyWebsiteNameTitleService", () => {
        test("updates only the title parts containing the previous name and allows rollback", () => {
            let currentParts = {
                website: "My Odoo Site - Odoo",
                page: "Home",
                other: "Odoo is cool",
            };

            const titleServiceMock = {
                getParts: () => currentParts,
                setParts: (parts) => {
                    currentParts = { ...currentParts, ...parts };
                },
            };

            const rollbacks = applyWebsiteName(titleServiceMock, "Test", "Odoo");

            expect(currentParts.website).toBe("My Odoo Site - Test");
            expect(currentParts.other).toBe("Test is cool");
            expect(currentParts.page).toBe("Home"); // Untouched

            // Verify Rollback restores title service parts
            rollbacks.forEach((r) => r());

            expect(currentParts.website).toBe("My Odoo Site - Odoo");
            expect(currentParts.other).toBe("Odoo is cool");
        });
    });
    describe("applyFavicon", () => {
        test("removes all previous icons and recreates them with the new URL", () => {
            // 1. Create a detached HTML document just for this test
            const mockDoc = document.implementation.createHTMLDocument("Mocked Doc");

            // 2. Add fake favicons to our isolated document
            ["icon", "shortcut icon", "apple-touch-icon"].forEach((relType) => {
                const link = mockDoc.createElement("link");
                link.rel = relType;
                link.href = "old-favicon.ico";
                mockDoc.head.appendChild(link);
            });

            // 3. Call applyFavicon by passing our isolated document
            applyFavicon("new-favicon.ico", mockDoc);

            // 4. Assert on the isolated document
            const newIcons = Array.from(mockDoc.head.querySelectorAll("link[rel*='icon']"));
            const rels = newIcons.map((link) => link.rel);

            expect(rels.includes("icon")).toBe(true);
            expect(rels.includes("shortcut icon")).toBe(true);
            expect(rels.includes("apple-touch-icon")).toBe(true);

            newIcons.forEach((link) => {
                expect(link.getAttribute("href")).toBe("new-favicon.ico");
            });
        });
    });
});

describe("WebsiteBrandingPlugin (Save & Discard Flows)", () => {
    let plugin;
    let rootElement;
    let ormCallSpy;

    beforeEach(() => {
        // 1. Patch the utility to prevent escaping the Hoot sandbox
        patch(applyFavicon, {});

        // 2. Mock a basic DOM (rootElement) simulating the website header
        rootElement = document.createElement("div");
        rootElement.innerHTML = `
            <header>
                <a class="navbar-brand">
                    <span>Old Name</span>
                </a>
                
                <div class="navbar-brand logo">
                    <span>
                        <img src="/old_logo.png" />
                    </span>
                </div>
            </header>
        `;
        // 3. Mock ORM to track payloads sent during save
        ormCallSpy = [];
        const mockOrm = {
            read: async () => [{ favicon: true }],
            searchCount: async () => 1, // <--- AJOUTER CETTE LIGNE
            call: async (model, method, args) => {
                ormCallSpy.push({ model, method, args });
                // Simulate ORM returning saved data
                return {
                    name: args[1].name || "Old Name",
                    has_favicon: !!args[1].favicon,
                    has_logo: !!args[1].logo,
                };
            },
        };

        // 4. Mock Media Dependency
        const mockMedia = {
            openMediaDialog: async (options) => {
                const fakeElement = document.createElement("img");
                fakeElement.src = "/new_image.png";
                fakeElement.dataset.id = "42"; // Fake attachment ID
                options.save(fakeElement);
            },
        };

        // 5. Create the context payload for the Plugin constructor
        const pluginContext = {
            document: rootElement,
            services: {
                website: { currentWebsite: { id: 1, name: "Old Name" } },
                orm: mockOrm,
                title: { getParts: () => ({}), setParts: () => {} },
            },
            dependencies: {
                media: mockMedia,
            },
        };

        // 6. Instantiate with the context to satisfy the base Plugin class
        plugin = new WebsiteBrandingPlugin(pluginContext);

        // Re-assigning manually as a fallback for internal Odoo plugin mechanics
        plugin.document = rootElement;
        plugin.services = pluginContext.services;
        plugin.dependencies = pluginContext.dependencies;

        // Initialize the plugin
        plugin.setup();
    });

    // ============================================================================
    // SAVE FLOW
    // ============================================================================
    test("Save flow: applies preview, saves via ORM, and cleans DOM to avoid COW", async () => {
        plugin.updateName("My Awesome Site");
        await plugin.updateLogo();
        await plugin.updateFavicon();

        expect(plugin.staged.name).toBe("My Awesome Site");
        expect(
            rootElement.querySelector("header .navbar-brand.logo span img").getAttribute("src")
        ).toBe("/new_image.png");

        await plugin.onWillSave();

        // Assert: Payload is correctly sent to ORM
        expect(ormCallSpy.length).toBe(1);
        const payload = ormCallSpy[0].args[1];
        expect(payload.name).toBe("My Awesome Site");
        expect(payload.logo).toBe(42);
        expect(payload.favicon).toBe(42);

        // Assert: Staged changes are cleared, and original values updated
        expect(Object.keys(plugin.staged).length).toBe(0);
        expect(plugin.originalValues.name).toBe("My Awesome Site");
    });

    // ============================================================================
    // DISCARD FLOW
    // ============================================================================

    test("Discard flow: applies previews, skips ORM, and restores Title Service", async () => {
        const setPartsSpy = [];
        plugin.services.title = {
            getParts: () => ({ website: "My Page - Old Name" }),
            setParts: (parts) => setPartsSpy.push(parts),
        };

        plugin.updateName("Discarded Name");
        await plugin.updateLogo();

        expect(plugin.staged.name).toBe("Discarded Name");

        expect(setPartsSpy.length).toBe(1);
        expect(setPartsSpy[0].website).toBe("My Page - Discarded Name");

        plugin.destroy();
        expect(ormCallSpy.length).toBe(0);
    });
});
