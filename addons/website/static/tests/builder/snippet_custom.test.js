import { createTestSnippets, getSnippetStructure } from "@html_builder/../tests/helpers";
import { Plugin } from "@html_editor/plugin";
import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    addPlugin,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Renaming custom snippets don't make an orm call", async () => {
    class TestSetupEditorPlugin extends Plugin {
        static id = "test.setup_editor_plugin";
        resources = {
            snippet_preview_dialog_bundles: ["web.assets_frontend"],
        };
    }
    addPlugin(TestSetupEditorPlugin);

    // Stub rename_snippet RPC to succeed if it is called
    onRpc("ir.ui.view", "rename_snippet", ({ args }) => true);

    const customSnippets = createTestSnippets({
        snippets: [
            {
                name: "Dummy Section",
                groupName: "custom",
                keywords: ["dummy"],
                content: `
        <section data-snippet="s_dummy">
            <div class="container">
                <div class="row">
                    <div class="col-lg-7">
                        <p>TEST</p>
                    </div>
                </div>
            </div>
        </section>
    `,
            },
        ],
        withName: true,
    });
    const snippets = {
        snippet_groups: [
            '<div name="Custom" data-oe-snippet-id="123" data-o-snippet-group="custom"><section data-snippet="s_snippet_group"></section></div>',
        ],
        snippet_structure: customSnippets.map((snippetDesc) => getSnippetStructure(snippetDesc)),
        snippet_custom: customSnippets.map((snippetDesc) => getSnippetStructure(snippetDesc)),
    };

    await setupWebsiteBuilder(
        `<section data-name="Dummy Section" data-snippet="s_dummy">
            <div class="container">
                <div class="row">
                    <div class="col-lg-7">
                        <p>TEST</p>
                        <p><a class="btn">BUTTON</a></p>
                    </div>
                </div>
            </div>
        </section>`,
        { snippets }
    );

    await contains(
        ".o-website-builder_sidebar .o_snippets_container .o_snippet[name='Custom'] button"
    ).click();
    await animationFrame();

    // Throw if any render_public_asset RPC happens during rename
    onRpc("ir.ui.view", "render_public_asset", () => {
        throw new Error("shouldn't make an rpc call on snippet rename");
    });

    await contains(
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_custom_snippet_edit button > .fa-pencil"
    ).click();
    expect(".o-overlay-item .modal-dialog:contains('Rename the block')").toHaveCount(1);
    await contains(".o-overlay-item .modal-dialog input#inputConfirmation").fill("new custom name");
    await contains(".o-overlay-item .modal-dialog footer>button:contains('Save')").click();
    expect(
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_custom_snippet_edit>span:contains('new custom name')"
    ).toHaveCount(1);
});
