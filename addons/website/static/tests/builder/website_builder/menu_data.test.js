import { describe, expect, test, beforeEach, Deferred, animationFrame } from "@odoo/hoot";
import { waitFor, waitForNone, click, queryOne } from "@odoo/hoot-dom";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { setupEditor } from "@html_editor/../tests/_helpers/editor";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { expectElementCount } from "@html_editor/../tests/_helpers/ui_expectations";
import { patchWithCleanup, mockService, onRpc, contains } from "@web/../tests/web_test_helpers";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { MenuDataPlugin } from "@website/builder/plugins/menu_data_plugin";
import { MenuDialog } from "@website/components/dialog/edit_menu";
import { SavePlugin } from "@html_builder/core/save_plugin";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { browser } from "@web/core/browser/browser";

defineWebsiteModels();

beforeEach(() => {
    onRpc("/web/exists", () => ({}));
    onRpc("/html_editor/link_preview_internal", () => ({}));
});

describe("NavbarLinkPopover", () => {
    test("should open a navbar popover when the selection is inside a top menu link and close outside of a top menu link", async () => {
        const { el } = await setupEditor(
            `<ul class="top_menu">
                <li>
                    <a class="nav-link" href="exists">
                        <span>Top Menu Item</span>
                    </a>
                </li>
            </ul>
            <p>Outside</p>`,
            {
                config: { Plugins: [...MAIN_PLUGINS, MenuDataPlugin, SavePlugin] },
            }
        );
        await expectElementCount(".o-we-linkpopover", 0);
        // selection inside a top menu link
        setSelection({ anchorNode: el.querySelector(".nav-link > span"), anchorOffset: 0 });
        await waitFor(".o-we-linkpopover");
        // remove link button replaced with sitemap button
        expect(".o-we-linkpopover:has(i.fa-chain-broken)").toHaveCount(0);
        expect(".o-we-linkpopover:has(button.js_edit_menu)").toHaveCount(1);
        // selection outside a top menu link
        setSelection({ anchorNode: el.querySelector("p"), anchorOffset: 0 });
        await expectElementCount(".o-we-linkpopover", 0);
    });

    test("should open a navbar popover when the selection is inside a top menu link and stay open if selection move in the same link", async () => {
        const { el } = await setupEditor(
            `<ul class="top_menu">
                <li>
                    <a class="nav-link" href="exists">
                        <span>Top Menu Item</span>
                    </a>
                </li>
            </ul>`,
            {
                config: { Plugins: [...MAIN_PLUGINS, MenuDataPlugin, SavePlugin] },
            }
        );
        expect(".o-we-linkpopover:has(button.js_edit_menu)").toHaveCount(0);
        // open navbar link popover
        setSelection({ anchorNode: el.querySelector(".nav-link > span"), anchorOffset: 0 });
        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover:has(button.js_edit_menu)").toHaveCount(1);
        // selection in the same link
        setSelection({ anchorNode: el.querySelector(".nav-link > span"), anchorOffset: 1 });
        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover:has(button.js_edit_menu)").toHaveCount(1);
    });

    test("should open a navbar popover when the selection is inside a top menu dropdown link", async () => {
        const { el } = await setupEditor(
            `<ul class="top_menu">
                <li>
                    <a class="nav-link" href="exists">
                        <span>Top Menu Item</span>
                    </a>
                </li>
                <div class="dropdown">
                    <a class="dropdown-toggle" data-bs-toggle="dropdown"></a>
                    <div class="dropdown-menu">
                        <li>
                            <a class="dropdown-item" href="exists">
                                <span>Dropdown Menu Item</span>
                            </a>
                        </li>
                    </div>
                </div>
            </ul>`,
            {
                config: { Plugins: [...MAIN_PLUGINS, MenuDataPlugin, SavePlugin] },
            }
        );
        expect(".o-we-linkpopover:has(button.js_edit_menu)").toHaveCount(0);
        // selection in dropdown menu
        setSelection({ anchorNode: el.querySelector(".dropdown-item > span"), anchorOffset: 0 });
        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover:has(button.js_edit_menu)").toHaveCount(1);
    });

    test("link redirection should be prefixed for links in the nav bar", async () => {
        patchWithCleanup(browser, {
            open(url) {
                expect.step("website page url prefixed");
                expect(url.pathname.startsWith("/@")).toBe(true);
            },
        });
        onRpc("/html_editor/link_preview_internal", () => ({}));
        onRpc("/contactus", () => ({}));

        // website pages should be prefixed with /@
        const { el } = await setupEditor(
            `<ul class="top_menu">
                <li>
                    <a class="nav-link" href="/contactus">
                        <span>Top Menu Item</span>
                    </a>
                </li>
            </ul>`,
            {
                config: { Plugins: [...MAIN_PLUGINS, MenuDataPlugin, SavePlugin] },
            }
        );

        await expectElementCount(".o-we-linkpopover", 0);
        // selection inside a top menu link
        setSelection({ anchorNode: el.querySelector(".nav-link > span"), anchorOffset: 0 });
        await waitFor(".o-we-linkpopover");
        await click(".o-we-linkpopover a");
        expect.verifySteps(["website page url prefixed"]);
    });
});

describe("MenuDialog", () => {
    test("after clicking on edit link button, a MenuDialog should appear", async () => {
        const { el } = await setupEditor(
            `<ul class="top_menu">
                <li>
                    <a class="nav-link" href="exists">
                        <span data-oe-id="5">Top Menu Item</span>
                    </a>
                </li>
            </ul>`,
            {
                config: { Plugins: [...MAIN_PLUGINS, MenuDataPlugin, SavePlugin] },
            }
        );
        patchWithCleanup(MenuDialog.prototype, {
            setup() {
                super.setup();
                this.website.pageDocument = el.ownerDocument;
            },
        });
        onRpc("/website/get_suggested_links", () => ({
            matching_pages: [],
            others: [],
        }));
        expect(".o-we-linkpopover:has(button.js_edit_menu)").toHaveCount(0);
        // open navbar link popover
        setSelection({ anchorNode: el.querySelector(".nav-link > span"), anchorOffset: 0 });
        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover:has(button.js_edit_menu)").toHaveCount(1);
        // click the link edit button
        await click(".o_we_edit_link");
        // check that MenuDialog is open and that name and url have been passed correctly
        await waitFor(".o_website_dialog");
        expect("input.form-control:not(#url_input)").toHaveValue("Top Menu Item");
        expect("#url_input").toHaveValue("exists");
    });
});

describe("EditMenuDialog", () => {
    const sampleMenuData = {
        fields: {
            id: 4,
            name: "Top Menu",
            url: "#",
            new_window: false,
            is_mega_menu: false,
            sequence: 0,
            parent_id: false,
        },
        children: [
            {
                fields: {
                    id: 5,
                    name: "Top Menu Item",
                    url: "#",
                    new_window: false,
                    is_mega_menu: false,
                    sequence: 10,
                    parent_id: 4,
                },
                children: [],
                is_homepage: true,
            },
        ],
        is_homepage: false,
    };

    beforeEach(() => {
        mockService("website", {
            get currentWebsite() {
                return {
                    id: 1,
                    default_lang_id: {
                        code: "en_US",
                    },
                    metadata: {
                        lang: "en_EN",
                    },
                };
            },
        });
    });
    test("after clicking on edit menu button, an EditMenuDialog should appear", async () => {
        const { el } = await setupEditor(
            `<ul class="top_menu">
                <li>
                    <a class="nav-link" href="exists">
                        <span>Top Menu Item</span>
                    </a>
                </li>
            </ul>`,
            {
                config: { Plugins: [...MAIN_PLUGINS, MenuDataPlugin, SavePlugin] },
            }
        );

        onRpc(({ model, method, args }) => {
            expect(model).toBe("website.menu");
            expect(method).toBe("get_tree");
            expect(args[0]).toBe(1);
            expect(args[1]).toBe(null);
            expect.step("get_tree");
            return sampleMenuData;
        });

        onRpc("/website/get_suggested_links", () => ({
            matching_pages: [],
            others: [],
        }));

        expect(".o-we-linkpopover:has(button.js_edit_menu)").toHaveCount(0);
        // open navbar link popover
        setSelection({ anchorNode: el.querySelector(".nav-link > span"), anchorOffset: 0 });
        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover:has(button.js_edit_menu)").toHaveCount(1);
        // click on edit menu button
        await click(".js_edit_menu");
        // check that EditMenuDialog is open with correct values
        await waitFor(".o_website_dialog");
        expect(".oe_menu_editor").toHaveCount(1);
        expect(".js_menu_label").toHaveText("Top Menu Item");
        expect.verifySteps(["get_tree"]);
    });

    test("after clicking on edit menu button in a sub-menu, an EditMenuDialog should appear", async () => {
        await setupEditor(
            `<ul class="nav" data-content_menu_id="4">
                <li>
                    <a class="nav-link" href="exists">
                        <span>[]Top Menu Item</span>
                    </a>
                </li>
            </ul>`,
            {
                config: { Plugins: [...MAIN_PLUGINS, MenuDataPlugin, SavePlugin] },
            }
        );

        onRpc(({ model, method, args }) => {
            expect(model).toBe("website.menu");
            expect(method).toBe("get_tree");
            expect(args[0]).toBe(1);
            expect(args[1]).toBe(4);
            expect.step("get_tree");
            return sampleMenuData;
        });

        onRpc("/website/get_suggested_links", () => ({
            matching_pages: [],
            others: [],
        }));

        await waitFor(".o-we-linkpopover");
        await click(".js_edit_menu");
        await waitFor(".o_website_dialog");
        expect.verifySteps(["get_tree"]);
    });

    test("clicking save in the EditMenuDialog should not clear the editor changes", async () => {
        const { getEditor } = await setupWebsiteBuilder(
            // Using tel: as link to avoid having to mock fetching metadata for link preview
            // This does not influence the test in any way
            `<ul class="top_menu">
                <li>
                    <a class="nav-link" href="tel: 123" contenteditable="true">
                        <span>Top Menu Item</span>
                    </a>
                </li>
            </ul>
            <section>
                <p>TEXT</p>
            </section>`,
            {
                openEditor: true,
            }
        );

        onRpc(({ method, model, args }) => {
            if (method === "save" && model === "ir.ui.view") {
                expect(args[1]).toInclude("EDITED TEXT");
                expect.step("editor_has_saved");
            }
            return sampleMenuData;
        });

        onRpc("/website/get_suggested_links", () => ({
            matching_pages: [],
            others: [],
        }));

        const editor = getEditor();

        // add some text
        var p = queryOne(":iframe section > p");
        setSelection({ anchorNode: p, anchorOffset: 0 });
        await insertText(editor, "EDITED ");
        expect(p).toHaveInnerHTML("EDITED TEXT");

        // open navbar link popover
        setSelection({ anchorNode: queryOne(":iframe .nav-link > span"), anchorOffset: 0 });

        // open menu editor and save
        await waitFor(".o-we-linkpopover");
        await click(queryOne("button.js_edit_menu"));
        await waitFor("footer.modal-footer");
        await click(queryOne(".modal-footer > button.btn-primary"));
        await waitForNone(".modal");
        expect.verifySteps(["editor_has_saved"]);
    });

    describe("should suggest to create the page if it does not exists", () => {
        // NOTE: we use `window.location.origin` as this is what is used by
        // `isAbsoluteURLInCurrentDomain` to tell it is the same domain. If we
        // simply use a relative url, the logic in `urlToCheck` incorrectly
        // consider the url to be external because it is confused by the mocks
        const topMenuUrl = new URL("/top-menu-url", window.location.origin).toString();
        const sampleMenuData = {
            fields: {
                id: 4,
                name: "Top Menu",
                url: "#",
                new_window: false,
                is_mega_menu: false,
                sequence: 0,
                parent_id: false,
            },
            children: [
                {
                    fields: {
                        id: 5,
                        name: "Top Menu Item",
                        url: topMenuUrl,
                        new_window: false,
                        is_mega_menu: false,
                        sequence: 10,
                        parent_id: 4,
                    },
                    children: [],
                    is_homepage: true,
                },
            ],
            is_homepage: false,
        };

        test("existing page do not have 'Create Page' button", async () => {
            await setupWebsiteBuilder("", { headerContent: `<header>header</header>` });
            await contains(":iframe header").click();

            onRpc("website.menu", "get_tree", () => sampleMenuData);
            onRpc("/website/check_existing_link", async (request) => {
                const { params } = await request.json();
                expect(params.link).toEqual("/top-menu-url");
                return true;
            });
            await contains("button:contains('Edit Menu')").click();

            expect("button:contains('Create Page')").toHaveCount(0);
        });
        test("non-existing page have 'Create Page' button", async () => {
            await setupWebsiteBuilder("", { headerContent: `<header>header</header>` });
            await contains(":iframe header").click();

            onRpc("website.menu", "get_tree", () => sampleMenuData);
            onRpc("/website/check_existing_link", async (request) => {
                const { params } = await request.json();
                expect(params.link).toEqual("/top-menu-url");
                return false;
            });
            await contains("button:contains('Edit Menu')").click();

            expect("button:contains('Create Page')").toHaveCount(1);
        });

        test("new menu with non-existing page have 'Create Page' button even if creation completes before it was indicated as non-existing in the creation dialog", async () => {
            const builder = await setupWebsiteBuilder("", {
                headerContent: `<header>header</header>`,
            });
            await contains(":iframe header").click();

            onRpc("website.menu", "get_tree", () => ({ ...sampleMenuData, children: [] }));
            await contains("button:contains('Edit Menu')").click();

            patchWithCleanup(MenuDialog.prototype, {
                setup() {
                    super.setup();
                    this.website.pageDocument = builder.getEditableContent().ownerDocument;
                },
                onClickOk() {
                    // little lie to avoid calling `toRelativeIfSameDomain`,
                    // so that we still have the absolute url (see NOTE above)
                    this.props.isMegaMenu = true;
                    super.onClickOk();
                    this.props.isMegaMenu = false;
                },
            });

            await contains("a:contains('Add Menu Item')").click();

            const deferred = new Deferred();
            onRpc("/website/check_existing_link", async (request) => {
                const { params } = await request.json();
                expect(params.link).toEqual("/top-menu-url");
                expect.step("check existing");
                await deferred;
                return false;
            });

            await contains("label:contains('Title') + * input").fill("New menu name");
            await contains("label:contains('Url') + * input").fill(topMenuUrl);
            await expect.waitForSteps(["check existing"]);
            await contains("button:contains('Continue')").click();

            expect("button:contains('Create Page')").toHaveCount(0);
            deferred.resolve();
            // the request is done again by "Edit Menu"
            await expect.waitForSteps(["check existing"]);
            await animationFrame();
            expect("button:contains('Create Page')").toHaveCount(1);
        });
    });
});
