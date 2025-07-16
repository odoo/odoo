import { Builder } from "@html_builder/builder";
import { CORE_PLUGINS } from "@html_builder/core/core_plugins";
import { Img } from "@html_builder/core/img";
import { SetupEditorPlugin } from "@html_builder/core/setup_editor_plugin";
import { LocalOverlayContainer } from "@html_editor/local_overlay_container";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { after } from "@odoo/hoot";
import { animationFrame, queryOne } from "@odoo/hoot-dom";
import { Component, onMounted, useRef, useState, useSubEnv, xml } from "@odoo/owl";
import {
    defineModels,
    models,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
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

function getSnippetView(snippets) {
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

function getSnippetStructure({ name, content, keywords = [], groupName, imagePreview = "" }) {
    keywords = keywords.join(", ");
    return `<div name="${name}" data-oe-snippet-id="123" data-o-image-preview="${imagePreview}" data-oe-keywords="${keywords}" data-o-group="${groupName}">${content}</div>`;
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
 * @param {*} options.styleContent
 * @returns {Promise<{ editor: Editor, contentEl: HTMLElement, builderEl: HTMLElement, snippetContent: String}>}
}}
 */
export async function setupHTMLBuilder(
    content = "",
    { headerContent = "", snippetContent, dropzoneSelectors, styleContent } = {}
) {
    defineMailModels(); // fuck this shit

    defineModels([IrUiView]);

    patchWithCleanupImg();

    // const snippetsDescription = { name: "Test", groupName: "a", content: snippetContentStr };
    // [{ name: "Test", groupName: "a", content: snippetContentStr }];

    const snippets = {
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
        snippet_content: snippetContent || [
            `<section class="s_test" data-snippet="s_test" data-name="Test">
            <div class="test_a"></div>
            </section>`,
        ],
    };

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

    const BuilderTestPlugins = registry.category("builder-test-plugins").getAll();
    Plugins.push(...BuilderTestPlugins);

    let _resolve;
    const prom = new Promise((resolve) => {
        _resolve = resolve;
    });

    // hack to get a promise that resolves when editor is ready
    patchWithCleanup(SetupEditorPlugin.prototype, {
        setup() {
            super.setup();
            _resolve();
        },
    });
    let attachedEditor;
    const comp = await mountWithCleanup(BuilderContainer, {
        props: {
            content,
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
        editor: attachedEditor,
        contentEl: comp.iframeRef.el.contentDocument.body.firstChild.firstChild,
        builderEl: comp.env.builderRef.el.querySelector(".o-website-builder_sidebar"),
        snippetContent: snippets.snippet_content.join(""),
    };
}

export function addBuilderPlugin(Plugin) {
    registry.category("builder-test-plugins").add(Plugin.id, Plugin);
    after(() => {
        registry.category("builder-test-plugins").remove(Plugin.id);
    });
}

export function addBuilderOption({
    selector,
    exclude,
    applyTo,
    template,
    OptionComponent,
    sequence,
    cleanForSave,
    props,
}) {
    const pluginId = uniqueId("test-option");
    const option = {
        OptionComponent: OptionComponent,
        template,
        selector,
        exclude,
        applyTo,
        cleanForSave,
        props,
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
