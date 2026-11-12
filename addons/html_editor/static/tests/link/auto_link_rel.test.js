import { Plugin } from "@html_editor/plugin";
import { expect, test } from "@odoo/hoot";
import { click, fill, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { setupEditor } from "../_helpers/editor";
import { cleanLinkArtifacts } from "../_helpers/format";
import { getContent } from "../_helpers/selection";
import { pasteText } from "../_helpers/user_actions";

function makeProviderPlugin(id, provider) {
    return class extends Plugin {
        static id = id;
        resources = {
            auto_link_rel_providers: provider,
        };
    };
}

/**
 * A plugin registering one advanced popover option per given `rel` token,
 * mirroring what website does. An auto token is only applied when such an
 * option backs it, so the providers above need this to have any effect.
 */
function makeRelOptionsPlugin(id, values) {
    return class extends Plugin {
        static id = id;
        resources = {
            advanced_popover_options: values.map((value) => ({
                id: value,
                label: value,
                description: value,
                attribute: "rel",
                value,
                isMultiValueAttr: true,
            })),
        };
    };
}

test("rel tokens of several providers accumulate on top of defaultLinkAttributes", async () => {
    const { editor, el } = await setupEditor("<p>ab[]cd</p>", {
        config: {
            defaultLinkAttributes: { rel: "noreferrer noopener" },
            includePlugins: [
                makeRelOptionsPlugin("test_options", ["nofollow", "sponsored"]),
                makeProviderPlugin("test_nofollow_provider", () => ["nofollow"]),
                makeProviderPlugin("test_sponsored_provider", () => ["sponsored"]),
            ],
        },
    });
    pasteText(editor, "https://odoo.com/");
    expect(cleanLinkArtifacts(getContent(el))).toBe(
        '<p>ab<a href="https://odoo.com/" rel="noreferrer noopener nofollow sponsored">' +
            "https://odoo.com/</a>[]cd</p>"
    );
});

test("a rel token no advanced popover option carries is not applied", async () => {
    const { editor, el } = await setupEditor("<p>ab[]cd</p>", {
        config: {
            includePlugins: [
                makeRelOptionsPlugin("test_options", ["sponsored"]),
                makeProviderPlugin("test_provider", () => ["nofollow"]),
            ],
        },
    });
    pasteText(editor, "https://odoo.com/");
    expect(cleanLinkArtifacts(getContent(el))).toBe(
        '<p>ab<a href="https://odoo.com/">https://odoo.com/</a>[]cd</p>'
    );
});

test("an option forced for the url is ticked and disabled, and released when it stops matching", async () => {
    await setupEditor("<p>H[ell]o</p>", {
        config: {
            allowStripDomain: false,
            includePlugins: [
                makeRelOptionsPlugin("test_options", ["nofollow"]),
                makeProviderPlugin("test_provider", (url) =>
                    url.includes("/doc/") ? ["nofollow"] : []
                ),
            ],
        },
    });
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar [data-icon='link']");
    const urlInput = await waitFor(".o-we-linkpopover input.o_we_href_input_link");
    urlInput.focus();
    await fill("/doc/1");
    await click(await waitFor(".o-we-linkpopover button:not([disabled]) [data-icon='settings']"));
    const checkbox = ".o_advance_option_panel .o_seo_option_row input[type='checkbox']";
    await waitFor(checkbox);
    expect(checkbox).toBeChecked();
    expect(checkbox).not.toBeEnabled();
    await click(".o_advance_option_panel button[data-icon='keyboard_arrow_left']");
    await contains(".o-we-linkpopover input.o_we_href_input_link").edit("https://example.com", {
        confirm: false,
    });
    await click(await waitFor(".o-we-linkpopover button:not([disabled]) [data-icon='settings']"));
    await waitFor(checkbox);
    // The url no longer matches: the option is released.
    expect(checkbox).toBeEnabled();
});
