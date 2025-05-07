import { describe, expect, test } from "@odoo/hoot";
import { waitFor, waitForNone, click } from "@odoo/hoot-dom";
import { defineWebsiteModels } from "../website_helpers";
import { setupEditor } from "@html_editor/../tests/_helpers/editor";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { patchWithCleanup, mockService, onRpc } from "@web/../tests/web_test_helpers";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { MenuDataPlugin } from "@html_builder/website_builder/plugins/menu_data_plugin";
import { MenuDialog } from "@website/components/dialog/edit_menu";

defineWebsiteModels();

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
                config: { Plugins: [...MAIN_PLUGINS, MenuDataPlugin] },
            }
        );
        expect(".o-we-linkpopover").toHaveCount(0);
        // selection inside a top menu link
        setSelection({ anchorNode: el.querySelector(".nav-link > span"), anchorOffset: 0 });
        await waitFor(".o-we-linkpopover");
        // remove link button replaced with sitemap button
        expect(".o-we-linkpopover:has(i.fa-chain-broken)").toHaveCount(0);
        expect(".o-we-linkpopover:has(i.fa-sitemap)").toHaveCount(1);
        // selection outside a top menu link
        setSelection({ anchorNode: el.querySelector("p"), anchorOffset: 0 });
        await waitForNone(".o-we-linkpopover");
        expect(".o-we-linkpopover").toHaveCount(0);
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
                config: { Plugins: [...MAIN_PLUGINS, MenuDataPlugin] },
            }
        );
        expect(".o-we-linkpopover:has(i.fa-sitemap)").toHaveCount(0);
        // open navbar link popover
        setSelection({ anchorNode: el.querySelector(".nav-link > span"), anchorOffset: 0 });
        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover:has(i.fa-sitemap)").toHaveCount(1);
        // selection in the same link
        setSelection({ anchorNode: el.querySelector(".nav-link > span"), anchorOffset: 1 });
        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover:has(i.fa-sitemap)").toHaveCount(1);
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
                config: { Plugins: [...MAIN_PLUGINS, MenuDataPlugin] },
            }
        );
        expect(".o-we-linkpopover:has(i.fa-sitemap)").toHaveCount(0);
        // selection in dropdown menu
        setSelection({ anchorNode: el.querySelector(".dropdown-item > span"), anchorOffset: 0 });
        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover:has(i.fa-sitemap)").toHaveCount(1);
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
                config: { Plugins: [...MAIN_PLUGINS, MenuDataPlugin] },
            }
        );
        patchWithCleanup(MenuDialog.prototype, {
            setup() {
                super.setup();
                this.website.pageDocument = el.ownerDocument;
            },
        });
        expect(".o-we-linkpopover:has(i.fa-sitemap)").toHaveCount(0);
        // open navbar link popover
        setSelection({ anchorNode: el.querySelector(".nav-link > span"), anchorOffset: 0 });
        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover:has(i.fa-sitemap)").toHaveCount(1);
        // click the link edit button
        await click(".o_we_edit_link");
        // check that MenuDialog is open and that name and url have been passed correctly
        await waitFor(".o_website_dialog");
        expect("input.form-control:not(#url_input)").toHaveValue("Top Menu Item");
        expect("#url_input").toHaveValue("exists");
    });
});

describe("EditMenuDialog", () => {
    test("after clicking on edit menu button, an EditMenuDialog should appear", async () => {
        onRpc(({ method, model, args, kwargs }) => {
            expect(model).toBe("website.menu");
            expect(method).toBe("get_tree");
            expect(args[0]).toBe(1);
            return {
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
                            url: "exists",
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
        });
        const { el } = await setupEditor(
            `<ul class="top_menu">
                <li>
                    <a class="nav-link" href="exists">
                        <span>Top Menu Item</span>
                    </a>
                </li>
            </ul>`,
            {
                config: { Plugins: [...MAIN_PLUGINS, MenuDataPlugin] },
            }
        );
        mockService("website", {
            get currentWebsite() {
                return {
                    id: 1,
                    metadata: {
                        lang: "en_EN",
                    },
                };
            },
        });
        expect(".o-we-linkpopover:has(i.fa-sitemap)").toHaveCount(0);
        // open navbar link popover
        setSelection({ anchorNode: el.querySelector(".nav-link > span"), anchorOffset: 0 });
        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover:has(i.fa-sitemap)").toHaveCount(1);
        // click on edit menu button
        await click(".js_edit_menu");
        // check that EditMenuDialog is open with correct values
        await waitFor(".o_website_dialog");
        expect(".oe_menu_editor").toHaveCount(1);
        expect(".js_menu_label").toHaveText("Top Menu Item");
    });
});
