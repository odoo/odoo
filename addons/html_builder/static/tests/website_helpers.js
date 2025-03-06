import { Builder } from "@html_builder/builder";
import { SetupEditorPlugin } from "@html_builder/core/plugins/setup_editor_plugin";
import { EditInteractionPlugin } from "@html_builder/website_builder/plugins/edit_interaction_plugin";
import { WebsiteSessionPlugin } from "@html_builder/website_builder/plugins/website_session_plugin";
import { WebsiteBuilder } from "@html_builder/website_preview/website_builder_action";
import { setContent } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { defineMailModels, startServer } from "@mail/../tests/mail_test_helpers";
import { after, describe } from "@odoo/hoot";
import { advanceTime, animationFrame, click, queryOne, waitFor } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    getService,
    mockService,
    models,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { loadBundle } from "@web/core/assets";
import { isBrowserFirefox } from "@web/core/browser/feature_detection";
import { registry } from "@web/core/registry";
import { uniqueId } from "@web/core/utils/functions";
import { WebClient } from "@web/webclient/webclient";
import { getWebsiteSnippets } from "./snippets_getter.hoot";

class Website extends models.Model {
    _name = "website";
    get_current_website() {
        return [1];
    }
}

class IrUiView extends models.Model {
    _name = "ir.ui.view";
    render_public_asset() {
        return getWebsiteSnippets();
    }
}

export const exampleWebsiteContent = '<h1 class="title">Hello</h1>';

export const invisibleEl =
    '<div class="s_invisible_el o_snippet_invisible" data-name="Invisible Element" data-invisible="1"></div>';

export const wrapExample = `<div id="wrap" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch">${exampleWebsiteContent}</div>`;

export function defineWebsiteModels() {
    describe.current.tags("desktop");
    defineMailModels();
    defineModels([Website, IrUiView]);
}

/**
 * This helper will be moved to website. Prefer using setupHTMLBuilder
 * for builder-specific tests
 */
export async function setupWebsiteBuilder(
    websiteContent,
    {
        snippets,
        openEditor = true,
        loadIframeBundles = false,
        hasToCreateWebsite = true,
        styleContent,
        headerContent = "",
        beforeWrapwrapContent = "",
    } = {}
) {
    // TODO: fix when the iframe is reloaded and become empty (e.g. discard button)
    if (hasToCreateWebsite) {
        const pyEnv = await startServer();
        pyEnv["website"].create({});
    }
    registry.category("services").remove("website_edit");
    let editor;
    let editableContent;
    await mountWithCleanup(WebClient);
    let originalIframeLoaded;
    let resolveIframeLoaded = () => {};
    const iframeLoaded = new Promise((resolve) => {
        resolveIframeLoaded = (el) => {
            const iframe = el;
            if (styleContent) {
                const style = iframe.contentDocument.createElement("style");
                style.innerHTML = styleContent;
                iframe.contentDocument.head.appendChild(style);
            }
            iframe.contentDocument.documentElement.setAttribute(
                "data-main-object",
                "website.page(4,)"
            );
            iframe.contentDocument.body.innerHTML = `
                ${beforeWrapwrapContent}
                <div id="wrapwrap">${headerContent} <div id="wrap" class="oe_structure oe_empty" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch">${websiteContent}</div></div>`;
            resolve(el);
        };
    });

    patchWithCleanup(WebsiteBuilder.prototype, {
        setup() {
            super.setup();
            originalIframeLoaded = this.iframeLoaded;
        },
        get systrayProps() {
            return {
                onNewPage: this.onNewPage.bind(this),
                onEditPage: this.onEditPage.bind(this),
                iframeLoaded: iframeLoaded,
            };
        },
        get menuProps() {
            const props = super.menuProps;
            props.iframeLoaded = iframeLoaded;
            return props;
        },
        loadAssetsEditBundle() {
            // To instantiate interactions in the iframe test we need to
            // load the edit and frontend bundle in it. The problem is that
            // Hoot does not have control of this iframe and therefore
            // does not mock anything in it (location, rpc, ...).
        },
    });
    await getService("action").doAction({
        name: "Website Builder",
        tag: "egg_website_preview",
        type: "ir.actions.client",
    });

    patchWithCleanup(EditInteractionPlugin.prototype, {
        setup() {
            super.setup();
            // See loadAssetsEditBundle override in WebsiteBuilder patch.
            this.websiteEditService = {
                update: () => {},
                stop: () => {},
            };
        },
    });

    patchWithCleanup(Builder.prototype, {
        setup() {
            super.setup();
            editor = this.editor;
        },
    });

    patchWithCleanup(SetupEditorPlugin.prototype, {
        setup() {
            super.setup();
            editableContent = this.getEditableElements(
                '.oe_structure.oe_empty, [data-oe-type="html"]'
            )[0];
        },
    });

    patchWithCleanup(WebsiteSessionPlugin.prototype, {
        getSession() {
            return {};
        },
    });

    if (snippets) {
        patchWithCleanup(IrUiView.prototype, {
            render_public_asset: () => getSnippetView(snippets),
        });
    }

    const iframe = queryOne("iframe[data-src^='/website/force/1']");
    if (loadIframeBundles) {
        loadBundle("html_builder.inside_builder_style", {
            targetDoc: iframe.contentDocument,
        });

        loadBundle("web.assets_frontend", {
            targetDoc: iframe.contentDocument,
            js: false,
        });
    }
    if (isBrowserFirefox()) {
        await originalIframeLoaded;
    }
    resolveIframeLoaded(iframe);
    await animationFrame();
    if (openEditor) {
        await openBuilderSidebar();
    }
    return {
        getEditor: () => editor,
        getEditableContent: () => editableContent,
    };
}

export async function openBuilderSidebar() {
    // The next line allow us to await asynchronous fetches and cache them before it is used
    await Promise.all([getWebsiteSnippets(), loadBundle("html_builder.assets")]);

    await click(".o-website-btn-custo-primary");
    // linked to the setTimeout in the WebsiteBuilder component
    await advanceTime(200);
    await animationFrame();
}

export function addPlugin(Plugin) {
    registry.category("website-plugins").add(Plugin.id, Plugin);
    after(() => {
        registry.category("website-plugins").remove(Plugin.id);
    });
}

export function addOption({
    selector,
    exclude,
    applyTo,
    template,
    Component,
    sequence,
    cleanForSave,
    props,
}) {
    const pluginId = uniqueId("test-option");
    const Class = makeOptionPlugin({
        pluginId,
        OptionComponent: Component,
        template,
        selector,
        exclude,
        applyTo,
        sequence,
        cleanForSave,
        props,
    });
    registry.category("website-plugins").add(pluginId, Class);
    after(() => {
        registry.category("website-plugins").remove(pluginId);
    });
}
function makeOptionPlugin({
    pluginId,
    template,
    selector,
    exclude,
    applyTo,
    sequence,
    OptionComponent,
    cleanForSave,
    props,
}) {
    const option = {
        OptionComponent,
        template,
        selector,
        exclude,
        applyTo,
        cleanForSave,
        props,
    };

    const Class = {
        [pluginId]: class extends Plugin {
            static id = pluginId;
            resources = {
                builder_options: sequence ? withSequence(sequence, option) : option,
            };
        },
    }[pluginId];

    return Class;
}

export function addActionOption(actions = {}) {
    const pluginId = uniqueId("test-action-plugin");
    class P extends Plugin {
        static id = pluginId;
        resources = {
            builder_actions: actions,
        };
    }
    registry.category("website-plugins").add(pluginId, P);
    after(() => {
        registry.category("website-plugins").remove(P);
    });
}

export function addDropZoneSelector(selector) {
    const pluginId = uniqueId("test-dropzone-selector");

    class P extends Plugin {
        static id = pluginId;
        resources = {
            dropzone_selector: [selector],
        };
    }

    registry.category("website-plugins").add(pluginId, P);
    after(() => {
        registry.category("website-plugins").remove(P);
    });
}

export async function modifyText(editor, editableContent) {
    setContent(editableContent, '<h1 class="title">H[]ello</h1>');
    editor.shared.history.addStep();
    await insertText(editor, "1");
}

export function getSnippetView(snippets) {
    const { snippet_groups, snippet_custom, snippet_structure, snippet_content } = snippets;
    return `
    <snippets id="snippet_groups" string="Categories">
        ${(snippet_groups || []).join("")}
    </snippets>
    <snippets id="snippet_structure" string="Structure">
        ${(snippet_structure || []).join("")}
    </snippets>
    <snippets id="snippet_custom" string="Custom">
        ${(snippet_custom || []).join("")}
    </snippets>
    <snippets id="snippet_content" string="Inner Content">
        ${(snippet_content || []).join("")}
    </snippets>`;
}

export function getSnippetStructure({
    name,
    content,
    keywords = [],
    groupName,
    imagePreview = "",
}) {
    keywords = keywords.join(", ");
    return `<div name="${name}" data-oe-snippet-id="123" data-o-image-preview="${imagePreview}" data-oe-keywords="${keywords}" data-o-group="${groupName}">${content}</div>`;
}

export function getInnerContent({
    name,
    content,
    keywords = [],
    imagePreview = "",
    thumbnail = "",
}) {
    keywords = keywords.join(", ");
    return `<div name="${name}" data-oe-type="snippet" data-oe-snippet-id="456" data-o-image-preview="${imagePreview}" data-oe-thumbnail="${thumbnail}" data-oe-keywords="${keywords}">${content}</div>`;
}

export const dummyBase64Img =
    "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAUA\n        AAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO\n            9TXL0Y4OHwAAAABJRU5ErkJggg==";

export async function setupWebsiteBuilderWithDummySnippet(content) {
    const getSnippetEl = (withColoredLevelClass = false) => {
        const className = withColoredLevelClass ? "s_test o_colored_level" : "s_test";
        return `<section class="${className}" data-snippet="s_test" data-name="Test">
            <div class="test_a"></div>
        </section>`;
    };
    const snippetsDescription = () => [{ name: "Test", groupName: "a", content: getSnippetEl() }];
    const snippetsStructure = {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: snippetsDescription().map((snippetDesc) =>
                getSnippetStructure(snippetDesc)
            ),
        },
    };
    const { getEditor, getEditableContent } = await setupWebsiteBuilder(
        content || "",
        snippetsStructure
    );
    const snippetContent = getSnippetEl(true);

    return { getEditor, getEditableContent, snippetContent };
}

export async function confirmAddSnippet(snippetName) {
    let previewSelector = `.o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap`;
    if (snippetName) {
        previewSelector += " [data-snippet='" + snippetName + "']";
    }
    await waitForSnippetDialog();
    await contains(previewSelector).click();
    await animationFrame();
}

export async function insertCategorySnippet({ group, snippet } = {}) {
    await contains(
        `.o-snippets-menu #snippet_groups .o_snippet${
            group ? `[data-snippet-group=${group}]` : ""
        } .o_snippet_thumbnail .o_snippet_thumbnail_area`
    ).click();
    await confirmAddSnippet(snippet);
}

export async function waitForSnippetDialog() {
    await animationFrame();
    await loadBundle("html_builder.iframe_add_dialog", {
        targetDoc: queryOne("iframe.o_add_snippet_iframe").contentDocument,
        js: false,
    });
    await waitFor(".o_add_snippet_dialog iframe.show.o_add_snippet_iframe");
}

export async function setupWebsiteBuilderWithSnippet(snippetName, options = {}) {
    mockService("website", {
        get currentWebsite() {
            return {
                metadata: {
                    defaultLangName: "English (US)",
                },
                id: 1,
            };
        },
    });
    const snippetEl = await getStructureSnippet(snippetName);
    return setupWebsiteBuilder(snippetEl.outerHTML, {
        ...options,
        hasToCreateWebsite: false,
    });
}

export async function getStructureSnippet(snippetName) {
    const html = await getWebsiteSnippets();
    const snippetsDocument = new DOMParser().parseFromString(html, "text/html");
    return snippetsDocument.querySelector(`[data-snippet=${snippetName}]`).cloneNode(true);
}

export async function insertStructureSnippet(editor, snippetName) {
    const snippetEl = await getStructureSnippet(snippetName);
    const parentEl = editor.editable.querySelector("#wrap") || editor.editable;
    parentEl.append(snippetEl);
    editor.shared.history.addStep();
}
