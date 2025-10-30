import { Builder } from "@html_builder/builder";
import { CORE_PLUGINS } from "@html_builder/core/core_plugins";
import { Img } from "@html_builder/core/img";
import { SetupEditorPlugin } from "@html_builder/core/setup_editor_plugin";
import { unformat } from "@html_editor/../tests/_helpers/format";
import { setContent } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { LocalOverlayContainer } from "@html_editor/local_overlay_container";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { after } from "@odoo/hoot";
import { animationFrame, waitForNone, queryOne, waitFor, advanceTime, tick } from "@odoo/hoot-dom";
import { Component, onMounted, useRef, useState, useSubEnv, xml } from "@odoo/owl";
import {
    contains,
    defineModels,
    models,
    mountWithCleanup,
    patchWithCleanup,
    waitUntilIdle,
} from "@web/../tests/web_test_helpers";
import { loadBundle } from "@web/core/assets";
import { isBrowserFirefox } from "@web/core/browser/feature_detection";
import { registry } from "@web/core/registry";
import { uniqueId } from "@web/core/utils/functions";

export function patchWithCleanupImg() {
    const defaultImg =
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z9DwHwAGBQKA3H7sNwAAAABJRU5ErkJggg==";
    patchWithCleanup(Img, {
        template: xml`<img t-att-data-src="props.src" t-att-alt="props.alt" t-att-class="props.class" t-att-style="props.style" t-att="props.attrs" src="${defaultImg}"/>`,
    });
    patchWithCleanup(Img.prototype, {
        loadImage: () => {},
        getSvg: function () {
            this.isSvg = () => false;
        },
    });
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

/**
 * Creates snippet structure HTML for test fixtures
 * @param {Object} options - Snippet structure configuration
 * @param {string} options.name - The display name of the snippet
 * @param {string} options.content - The HTML content of the snippet
 * @param {string[]} [options.keywords=[]] - Search keywords for the snippet
 * @param {string} options.groupName - The snippet group (category) name
 * @param {string} [options.imagePreview=""] - URL to preview image
 * @param {string|number} [options.moduleId=""] - Module ID if snippet belongs to a module
 * @param {string} [options.moduleDisplayName=""] - Human-readable module name
 * @returns {string} HTML string for the snippet structure
 */
export function getSnippetStructure({
    name,
    content,
    keywords = [],
    groupName,
    imagePreview = "",
    moduleId = "",
    moduleDisplayName = "",
}) {
    keywords = keywords.join(", ");
    return `<div name="${name}" data-oe-snippet-id="123" data-o-image-preview="${imagePreview}" data-oe-keywords="${keywords}" data-o-group="${groupName}" data-module-id="${moduleId}" data-module-display-name="${moduleDisplayName}">${content}</div>`;
}

class BuilderContainer extends Component {
    static template = xml`
        <div class="d-flex h-100 w-100" t-ref="container">
            <div class="o_website_preview flex-grow-1" t-ref="website_preview">
                <div class="o_iframe_container">
                    <iframe class="h-100 w-100" t-ref="iframe" t-on-load="onLoad"/>
                    <div t-if="this.state.isMobile" class="o_mobile_preview_layout">
                        <img alt="phone" src="/html_builder/static/img/phone.svg"/>
                    </div>
                </div>
            </div>
            <LocalOverlayContainer localOverlay="overlayRef" identifier="env.localOverlayContainerKey"/>
            <div t-if="state.isEditing" t-att-class="{'o_builder_sidebar_open': state.isEditing and state.showSidebar}" class="o-website-builder_sidebar border-start border-dark">
                <Builder t-props="this.getBuilderProps()"/>
            </div>
        </div>`;
    static components = { Builder, LocalOverlayContainer };
    static props = {
        content: String,
        editableSelector: String,
        headerContent: String,
        Plugins: Array,
        onEditorLoad: Function,
    };

    setup() {
        this.state = useState({ isMobile: false, isEditing: false, showSidebar: true });
        this.iframeRef = useRef("iframe");
        const originalIframeLoaded = new Promise((resolve) => {
            this._originalIframeLoadedResolve = resolve;
        });
        this.iframeLoaded = new Promise((resolve) => {
            onMounted(async () => {
                if (isBrowserFirefox()) {
                    await originalIframeLoaded;
                }

                const el = this.iframeRef.el;
                el.contentDocument.body.innerHTML = `<div id="wrapwrap">${this.props.headerContent}<div id="wrap" class="oe_structure oe_empty" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch">${this.props.content}</div></div>`;
                resolve(el);
            });
        });
        useSubEnv({
            builderRef: useRef("container"),
        });
    }

    onLoad() {
        this._originalIframeLoadedResolve();
    }

    getBuilderProps() {
        return {
            onEditorLoad: this.props.onEditorLoad,
            closeEditor: () => {},
            snippetsName: "",
            toggleMobile: () => {
                this.state.isMobile = !this.state.isMobile;
            },
            overlayRef: () => {},
            editableSelector: this.props.editableSelector,
            iframeLoaded: this.iframeLoaded,
            isMobile: this.state.isMobile,
            Plugins: this.props.Plugins,
        };
    }
}

class IrUiView extends models.Model {
    _name = "ir.ui.view";
    render_public_asset() {
        throw new Error("This should be implemented by some helper");
    }
}

/**
 * @typedef { import("@html_editor/editor").Editor } Editor
 *
 * @param {String} content
 * @param {Object} options
 * @param {String} options.headerContent
 * @param {*} options.snippetContent
 * @param {*} options.dropzoneSelectors
 * @param {*} options.snippets
 * @param {*} options.styleContent
 * @returns {Promise<{
 * getEditor: () => Editor,
 * getEditableContent: () => HTMLElement,
 * contentEl: HTMLElement,
 * builderEl: HTMLElement,
 * waitSidebarUpdated: () => Promise<void>
 * }>}
}}
 */
export async function setupHTMLBuilder(
    content = "",
    {
        editableSelector = "#wrapwrap",
        headerContent = "",
        snippetContent,
        dropzoneSelectors,
        snippets,
        styleContent,
    } = {}
) {
    defineMailModels();
    defineModels([IrUiView]);

    patchWithCleanupImg();

    if (!snippets) {
        snippets = {
            snippet_groups: [
                '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: [
                getSnippetStructure({
                    name: "Test",
                    groupName: "a",
                    content: `<section class="s_test" data-snippet="s_test" data-name="Test">
            <div class="test_a"></div>
            </section>`,
                }),
            ],
            // TODO: maybe we should use the same structure as in the snippets?
            snippet_content: snippetContent || [
                `<section class="s_test" data-snippet="s_test" data-name="Test">
            <div class="test_a"></div>
            </section>`,
            ],
        };
    }

    patchWithCleanup(IrUiView.prototype, {
        render_public_asset: () => getSnippetView(snippets),
    });

    const Plugins = [...CORE_PLUGINS];

    if (dropzoneSelectors) {
        const pluginId = uniqueId("test-dropzone-selector");

        class P extends Plugin {
            static id = pluginId;
            resources = {
                dropzone_selector: dropzoneSelectors,
            };
        }
        Plugins.push(P);
    }

    const BuilderPlugins = registry.category("builder-plugins").getAll();
    Plugins.push(...BuilderPlugins);

    let lastUpdatePromise;
    const waitSidebarUpdated = async () => {
        await attachedEditor.shared.operation.next();
        // The tick ensures that lastUpdatePromise has correctly been assigned
        await tick();
        await lastUpdatePromise;
        await animationFrame();
        await waitUntilIdle([comp.__owl__.app]);
    };
    patchWithCleanup(Builder.prototype, {
        setup() {
            super.setup();
            patchWithCleanup(this.env.editorBus, {
                trigger(eventName, detail) {
                    if (eventName === "DOM_UPDATED") {
                        lastUpdatePromise = detail.updatePromise;
                    }
                    return super.trigger(eventName, detail);
                },
            });
        },
    });

    let _resolve;
    const prom = new Promise((resolve) => {
        _resolve = resolve;
    });

    let editableContent;
    // hack to get a promise that resolves when editor is ready
    patchWithCleanup(SetupEditorPlugin.prototype, {
        setup() {
            super.setup();
            _resolve();
            editableContent = this.getEditableElements(
                '.oe_structure.oe_empty, [data-oe-type="html"]'
            )[0];
        },
    });

    let attachedEditor;
    const comp = await mountWithCleanup(BuilderContainer, {
        props: {
            content,
            editableSelector,
            headerContent,
            Plugins,
            onEditorLoad: (editor) => {
                attachedEditor = editor;
            },
        },
    });
    await comp.iframeLoaded;
    if (styleContent) {
        const iframeDocument = queryOne(":iframe");
        const styleEl = iframeDocument.createElement("style");
        styleEl.textContent = styleContent;
        iframeDocument.head.appendChild(styleEl);
    }
    comp.state.isEditing = true;
    await prom;
    await animationFrame();
    return {
        getEditor: () => attachedEditor,
        getEditableContent: () => editableContent,
        contentEl: comp.iframeRef.el.contentDocument.body.firstChild.firstChild,
        builderEl: comp.env.builderRef.el.querySelector(".o-website-builder_sidebar"),
        waitSidebarUpdated,
    };
}

export function addBuilderPlugin(Plugin) {
    registry.category("builder-plugins").add(Plugin.id, Plugin);
    after(() => {
        registry.category("builder-plugins").remove(Plugin.id);
    });
}

export function addBuilderOption(Option) {
    const pluginId = uniqueId("test-option");

    const P = {
        [pluginId]: class extends Plugin {
            static id = pluginId;
            resources = {
                builder_options: Option,
            };
        },
    }[pluginId];

    addBuilderPlugin(P);
}

export function addLegacyBuilderOption({
    selector,
    exclude,
    applyTo,
    template,
    Component,
    sequence,
    cleanForSave,
    props,
    editableOnly,
    title,
    reloadTarget,
}) {
    const pluginId = uniqueId("test-option");
    const option = {
        pluginId,
        OptionComponent: Component,
        template,
        selector,
        exclude,
        applyTo,
        sequence,
        cleanForSave,
        props,
        editableOnly,
        title,
        reloadTarget,
    };

    const P = {
        [pluginId]: class extends Plugin {
            static id = pluginId;
            resources = {
                builder_options: sequence ? withSequence(sequence, option) : option,
            };
        },
    }[pluginId];
    addBuilderPlugin(P);
}

export function addBuilderAction(actions = {}) {
    const pluginId = uniqueId("test-action-plugin");
    class P extends Plugin {
        static id = pluginId;
        resources = {
            builder_actions: actions,
        };
    }
    addBuilderPlugin(P);
}

/**
 * Returns the dragged helper when drag and dropping snippets.
 */
export function getDragHelper() {
    return document.body.querySelector(".o_draggable_dragging .o_snippet_thumbnail");
}

/**
 * Returns the dragged helper when drag and dropping elements from the page.
 */
export function getDragMoveHelper() {
    return document.body.querySelector(".o_drag_move_helper");
}

/**
 * Waits for the loading element added by the mutex to be removed, indicating
 * that the operation is over.
 */
export async function waitForEndOfOperation() {
    await advanceTime(500);
    await waitForNone(":iframe .o_loading_screen");
    await animationFrame();
}

export function addDropZoneSelector(selector) {
    const pluginId = uniqueId("test-dropzone-selector");

    class P extends Plugin {
        static id = pluginId;
        resources = {
            dropzone_selector: [selector],
        };
    }

    registry.category("builder-plugins").add(pluginId, P);
    after(() => {
        registry.category("builder-plugins").remove(P);
    });
}

export async function waitForSnippetDialog() {
    await animationFrame();
    await loadBundle("web.assets_frontend", {
        targetDoc: queryOne("iframe.o_add_snippet_iframe").contentDocument,
        js: false,
    });
    await loadBundle("html_builder.iframe_add_dialog", {
        targetDoc: queryOne("iframe.o_add_snippet_iframe").contentDocument,
        js: false,
    });
    await waitFor(".o_add_snippet_dialog iframe.show.o_add_snippet_iframe");
}

export async function modifyText(editor, editableContent) {
    setContent(editableContent, '<h1 class="title">H[]ello</h1>');
    editor.shared.history.addStep();
    await insertText(editor, "1");
}

// Snippet Testing Helpers
// Use createTestSnippets() for most cases to replace repetitive getSnippetsDescription functions
// Use getBasicSection() for simple HTML section generation

/**
 * Creates a basic HTML section structure for test snippets
 * @param {string} content - The content to place inside the section
 * @param {Object} [options={}] - Configuration options
 * @param {string} [options.name] - Name attribute for the section (data-name)
 * @param {string} [options.snippet="s_test"] - Snippet class and data-snippet value
 * @param {string} [options.additionalClassOnRoot=""] - Additional CSS classes for the root element
 * @returns {string} Formatted HTML section element
 */
export function getBasicSection(
    content,
    { name, snippet = "s_test", additionalClassOnRoot = "" } = {}
) {
    let classes = snippet;
    if (additionalClassOnRoot) {
        classes += ` ${additionalClassOnRoot}`;
    }
    return unformat(
        `<section class="${classes}" data-snippet="${snippet}" ${
            name ? `data-name="${name}"` : ""
        }><div class="test_a">${content}</div></section>`
    );
}

export function createTestSnippets({ snippets: snippetConfigs = [], withName = false }) {
    return snippetConfigs.map((snippetConfig) => {
        const {
            name,
            groupName = "a",
            content,
            innerHTML,
            keywords = [],
            imagePreview = "",
            moduleId,
            moduleDisplayName,
            additionalClassOnRoot,
            snippet: snippetId,
        } = snippetConfig;

        const finalContent =
            content ||
            getBasicSection(innerHTML || name, {
                name: withName ? name : "",
                snippet: snippetId || "s_test",
                additionalClassOnRoot,
            });

        const snippet = {
            name,
            groupName,
            content: finalContent,
            keywords,
            imagePreview,
            moduleId,
            moduleDisplayName,
        };

        return snippet;
    });
}

export async function confirmAddSnippet(snippetName) {
    let previewSelector = `.o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap`;
    if (snippetName) {
        previewSelector += ":has([data-snippet='" + snippetName + "'])";
    }
    await waitForSnippetDialog();
    await contains(previewSelector).click();
    await animationFrame();
}

export const dummyBase64Img =
    "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAUA\n        AAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO\n            9TXL0Y4OHwAAAABJRU5ErkJggg==";

export const exampleContent = '<h1 class="title">Hello</h1>';

export const wrapExample = `<div id="wrap" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch">${exampleContent}</div>`;

export async function setupHTMLBuilderWithDummySnippet(content) {
    const snippetEl = `<section class="s_test" data-snippet="s_test" data-name="Test">
            <div class="test_a"></div>
        </section>`;

    const snippetsDescription = createTestSnippets({
        snippets: [
            {
                name: "Test",
                groupName: "a",
                content: snippetEl,
            },
        ],
    });

    const snippetsStructure = {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: snippetsDescription.map((snippetDesc) =>
                getSnippetStructure(snippetDesc)
            ),
        },
    };

    return await setupHTMLBuilder(content || "", snippetsStructure);
}
