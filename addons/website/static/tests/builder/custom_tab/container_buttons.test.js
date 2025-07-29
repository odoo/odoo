import { expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
    addOption,
    getSnippetStructure,
    getInnerContent,
    getSnippetView,
    dummyBase64Img,
    addPlugin,
    addActionOption,
    waitForSnippetDialog,
} from "../website_helpers";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { animationFrame, Deferred, queryText, tick, waitFor } from "@odoo/hoot-dom";
import { undo } from "@html_editor/../tests/_helpers/user_actions";
import { Plugin } from "@html_editor/plugin";
import { BuilderAction } from "@html_builder/core/builder_action";

defineWebsiteModels();

const dummySnippet = `
    <section data-name="Dummy Section" data-snippet="s_dummy">
        <div class="container">
            <div class="row">
                <div class="col-lg-7">
                    <p>TEST</p>
                    <p><a class="btn">BUTTON</a></p>
                    <img src="${dummyBase64Img}"/>
                </div>
                <div class="col-lg-5">
                    <p>TEST</p>
                </div>
            </div>
        </div>
    </section>
`;

test("Use the sidebar 'remove' buttons", async () => {
    await setupWebsiteBuilder(dummySnippet);

    const removeSectionSelector =
        ".o_customize_tab .options-container > div:contains('Dummy Section') button.oe_snippet_remove";
    const removeColumnSelector =
        ".o_customize_tab .options-container > div:contains('Column') button.oe_snippet_remove";
    const removeImageSelector =
        ".o_customize_tab .options-container > div:contains('Image') button.oe_snippet_remove";

    await contains(":iframe .col-lg-7 img").click();
    await waitFor(".options-container");
    expect(removeSectionSelector).toHaveCount(1);
    expect(removeColumnSelector).toHaveCount(1);
    expect(removeImageSelector).toHaveCount(1);

    await contains(removeImageSelector).click();
    expect(":iframe .col-lg-7 img").toHaveCount(0);
    await contains(removeColumnSelector).click();
    expect(":iframe .col-lg-7").toHaveCount(0);
    await contains(removeSectionSelector).click();
    expect(":iframe section").toHaveCount(0);
});

test("Use the sidebar 'clone' buttons", async () => {
    await setupWebsiteBuilder(dummySnippet);

    const cloneSectionSelector =
        ".o_customize_tab .options-container > div:contains('Dummy Section') button.oe_snippet_clone";
    const cloneColumnSelector =
        ".o_customize_tab .options-container > div:contains('Column') button.oe_snippet_clone";

    await contains(":iframe .col-lg-7").click();
    await animationFrame();
    expect(cloneSectionSelector).toHaveCount(1);
    expect(cloneColumnSelector).toHaveCount(1);

    await contains(cloneColumnSelector).click();
    expect(":iframe .col-lg-7").toHaveCount(2);
    await contains(cloneSectionSelector).click();
    expect(":iframe section").toHaveCount(2);
    expect(":iframe .col-lg-7").toHaveCount(4);
    expect(":iframe .col-lg-5").toHaveCount(2);
});

test("Use the sidebar 'save snippet' buttons", async () => {
    addOption({
        selector: "a.btn",
        template: xml`<BuilderButton classAction="'dummy-class'"/>`,
    });
    const structureSnippetDesc = {
        name: "Dummy Section",
        groupName: "a",
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
        keywords: ["dummy"],
    };
    const innerContentDesc = {
        name: "Button",
        content: `<a data-snippet="s_button" class="btn o_snippet_drop_in_only" href="/contactus">Button</a></div>`,
    };
    const snippets = {
        snippet_groups: [
            '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
            '<div name="Custom" data-oe-thumbnail="custom.svg" data-oe-snippet-id="123" data-o-snippet-group="custom"><section data-snippet="s_snippet_group"></section></div>',
        ],
        snippet_structure: [getSnippetStructure(structureSnippetDesc)],
        snippet_content: [getInnerContent(innerContentDesc)],
        snippet_custom: [],
    };
    await setupWebsiteBuilder(dummySnippet, { snippets });

    onRpc("ir.ui.view", "save_snippet", ({ kwargs }) => {
        let { name, arch, snippet_key, thumbnail_url } = kwargs;
        // Add `data-snippet` if it is missing.
        if (!arch.includes("data-snippet")) {
            const spaceIndex = arch.indexOf(" ") + 1;
            arch =
                arch.slice(0, spaceIndex) +
                `data-snippet="${snippet_key}" ` +
                arch.slice(spaceIndex);
        }
        const customSnippet = `<div name="${name}" data-oe-type="snippet" data-oe-snippet-id="789" data-o-image-preview="" data-oe-thumbnail="${thumbnail_url}" data-oe-keywords="">${arch}</div>`;
        snippets.snippet_custom.push(customSnippet);
        return name;
    });
    onRpc("ir.ui.view", "render_public_asset", (args) => getSnippetView(snippets));

    const saveSectionSelector =
        ".o_customize_tab .options-container > div:contains('Dummy Section') button.oe_snippet_save";
    const saveColumnSelector =
        ".o_customize_tab .options-container > div:contains('Column') button.oe_snippet_save";
    const saveButtonSelector =
        ".o_customize_tab .options-container > div:contains('Button') button.oe_snippet_save";

    // Check that there is no custom section.
    const customGroupSelector =
        ".o-snippets-menu #snippet_groups .o_snippet[data-snippet-group='custom'] .o_snippet_thumbnail_area";
    expect(".o-snippets-menu div:contains('Custom Inner Content')").toHaveCount(0);
    expect(customGroupSelector).toHaveCount(0);

    await contains(":iframe .btn").click();
    await animationFrame();
    expect(saveSectionSelector).toHaveCount(1);
    expect(saveColumnSelector).toHaveCount(0);
    expect(saveButtonSelector).toHaveCount(1);

    // Save the snippets.
    await contains(saveButtonSelector).click();
    await contains(".o_dialog .btn:contains('Save')").click();
    expect(".o_notification_manager .o_notification_content").toHaveCount(1);
    await contains(".o_notification_manager .o_notification_close").click();

    await contains(saveSectionSelector).click();
    await contains(".o_dialog .btn:contains('Save')").click();
    expect(".o_notification_manager .o_notification_content").toHaveCount(1);

    // Check that the custom sections appeared.
    await contains(".o-website-builder_sidebar .o-snippets-tabs button:contains(Blocks)").click();
    expect(
        ".o-snippets-menu div:contains('Custom Inner Content') div[name='Custom Button']"
    ).toHaveCount(1);
    expect(customGroupSelector).toHaveCount(1);
    await contains(customGroupSelector).click();
    await waitForSnippetDialog();
    expect(
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe span:not(.visually-hidden):contains('Custom Dummy Section')"
    ).toHaveCount(1);
});

test("Use the sidebar 'create anchor' buttons", async () => {
    const websiteContent = `
        <section class="first" data-name="Dummy Section" data-snippet="s_dummy">
            <h1>Anchor test</h1>
        </section>
        <section class="second" data-name="Dummy Section" data-snippet="s_dummy">
            <p>test<p>
        </section>
        <section class="third" data-name="Dummy Section" data-snippet="s_dummy">
            <p>test<p>
        </section>
    `;
    await setupWebsiteBuilder(websiteContent);
    const anchorSelector =
        ".o_customize_tab .options-container > div:contains('Dummy Section') button.oe_snippet_anchor";
    const notificationContentSelector = ".o_notification_manager .o_notification_content";
    const notificationCloseSelector = ".o_notification_manager .o_notification_close";
    const notificationEditSelector = ".o_notification_manager .o_notification_buttons button";

    // Section with title should have the title as anchor.
    await contains(":iframe section.first").click();
    await animationFrame();
    expect(anchorSelector).toHaveCount(1);
    await contains(anchorSelector).click();
    expect(notificationContentSelector).toHaveCount(1);
    expect(queryText(notificationContentSelector)).toInclude("#Anchor-test");
    await contains(notificationCloseSelector).click();
    expect(":iframe section.first").toHaveAttribute("id", "Anchor-test");
    expect(":iframe section.first").toHaveAttribute("data-anchor", "true");

    // Section without title should have the `data-name` as anchor.
    await contains(":iframe section.second").click();
    await animationFrame();
    await contains(anchorSelector).click();
    await animationFrame();
    expect(queryText(notificationContentSelector)).toInclude("#Dummy-Section");
    await contains(notificationCloseSelector).click();
    expect(":iframe section.second").toHaveAttribute("id", "Dummy-Section");

    // Same data-name should be suffixed by a number.
    await contains(":iframe section.third").click();
    await animationFrame();
    await contains(anchorSelector).click();
    expect(queryText(notificationContentSelector)).toInclude("#Dummy-Section2");
    expect(":iframe section.third").toHaveAttribute("id", "Dummy-Section2");

    // Edit anchor.
    await contains(notificationEditSelector).click();
    expect(".o_dialog").toHaveCount(1);
    await contains(".o_dialog input").edit("Dummy-Section");
    await contains(".o_dialog button:contains('Save & Copy')").click();
    expect(".o_dialog input").toHaveClass("is-invalid");
    await contains(".o_dialog input").edit("new-anchor-name");
    await contains(".o_dialog button:contains('Save & Copy')").click();
    expect(".o_dialog").toHaveCount(0);
    expect(":iframe section.third").toHaveAttribute("id", "new-anchor-name");

    // Delete anchor
    await contains(anchorSelector).click();
    await contains(notificationEditSelector).click();
    await contains(".o_dialog button:contains('Remove')").click();
    expect(":iframe section.third").not.toHaveAttribute("id");
    expect(":iframe section.third").not.toHaveAttribute("data-anchor");
});

test("Clicking on the options container title selects the corresponding element", async () => {
    await setupWebsiteBuilder(dummySnippet);

    await contains(":iframe .col-lg-7").click();
    await animationFrame();
    expect(".o_customize_tab .options-container").toHaveCount(2);
    expect(".oe_overlay.oe_active").toHaveRect(":iframe .col-lg-7");

    await contains(".o_customize_tab .options-container span:contains('Dummy Section')").click();
    expect(".o_customize_tab .options-container").toHaveCount(1);
    expect(".oe_overlay.oe_active").toHaveRect(":iframe section");
});

test("Show the overlay preview when hovering an options container", async () => {
    await setupWebsiteBuilder(dummySnippet);

    await contains(":iframe .col-lg-7").click();
    expect(".overlay .o_overlay_options:not(.d-none)").toHaveCount(1);
    expect(".oe_overlay").toHaveCount(2);
    expect(".oe_overlay.oe_active").toHaveRect(":iframe .col-lg-7");

    await contains(".o_customize_tab .options-container span:contains('Dummy Section')").hover();
    expect(".overlay .o_overlay_options.d-none").toHaveCount(1);
    expect(".oe_overlay.oe_active.o_overlay_hidden").toHaveCount(1);
    expect(".oe_overlay.o_we_overlay_preview").toHaveRect(":iframe section");

    await contains(".o_customize_tab .options-container span:contains('Column')").hover();
    expect(".overlay .o_overlay_options.d-none").toHaveCount(1);
    expect(".oe_overlay.oe_active.o_we_overlay_preview").toHaveCount(1);
    expect(".oe_overlay.o_we_overlay_preview").toHaveRect(":iframe .col-lg-7");

    await contains(":iframe .col-lg-7").hover();
    expect(".overlay .o_overlay_options:not(.d-none)").toHaveCount(1);
    expect(".oe_overlay.o_we_overlay_preview").toHaveCount(0);
    expect(".oe_overlay.oe_active:not(.o_overlay_hidden)").toHaveRect(":iframe .col-lg-7");
});

test("applying option container button should wait for actions in progress", async () => {
    class TestPlugin extends Plugin {
        static id = "test";
        resources = {
            get_options_container_top_buttons: this.getButtons.bind(this),
        };

        getButtons(target) {
            return [
                {
                    class: "test_button fa fa-shield",
                    title: "Test",
                    handler: () => {
                        target.classList.add("overlayButton");
                    },
                },
            ];
        }
    }
    addPlugin(TestPlugin);
    const customActionDef = new Deferred();
    addActionOption({
        customAction: class extends BuilderAction {
            static id = "customAction";
            load() {
                return customActionDef;
            }
            apply({ editingElement }) {
                editingElement.classList.add("customAction");
            }
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderButton action="'customAction'"/>`,
    });

    const { getEditableContent, getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target o-paragraph">plop</div>
    `);
    const editor = getEditor();
    const editable = getEditableContent();

    await contains(":iframe .test-options-target").click();
    await contains("[data-action-id='customAction']").click();
    expect(editable).toHaveInnerHTML(`<div class="test-options-target o-paragraph">plop</div>`);

    await contains(".test_button").click();
    expect(editable).toHaveInnerHTML(`<div class="test-options-target o-paragraph">plop</div>`);

    customActionDef.resolve();
    await tick();
    expect(editable).toHaveInnerHTML(
        `<div class="test-options-target o-paragraph customAction overlayButton">plop</div>`
    );

    undo(editor);
    expect(editable).toHaveInnerHTML(
        `<div class="test-options-target o-paragraph customAction">plop</div>`
    );

    undo(editor);
    expect(editable).toHaveInnerHTML(`<div class="test-options-target o-paragraph">plop</div>`);
});
