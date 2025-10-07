import {
    confirmAddSnippet,
    getSnippetStructure,
    getSnippetView,
    patchWithCleanupImg,
    waitForEndOfOperation,
} from "@html_builder/../tests/helpers";
import { Builder } from "@html_builder/builder";
import { SetupEditorPlugin } from "@html_builder/core/setup_editor_plugin";
import { VersionControlPlugin } from "@html_builder/core/version_control_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { defineMailModels, startServer } from "@mail/../tests/mail_test_helpers";
import { after, describe } from "@odoo/hoot";
import { advanceTime, animationFrame, click, queryOne, tick, waitFor } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    getService,
    mockService,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { loadBundle } from "@web/core/assets";
import { isBrowserFirefox } from "@web/core/browser/feature_detection";
import { registry } from "@web/core/registry";
import { uniqueId } from "@web/core/utils/functions";
import { WebClient } from "@web/webclient/webclient";
import { EditInteractionPlugin } from "@website/builder/plugins/edit_interaction_plugin";
import { WebsiteSessionPlugin } from "@website/builder/plugins/website_session_plugin";
import { WebsiteBuilderClientAction } from "@website/client_actions/website_preview/website_builder_action";
import { WebsiteSystrayItem } from "@website/client_actions/website_preview/website_systray_item";
import { mockImageRequests } from "./image_test_helpers";
import { getWebsiteSnippets } from "./snippets_getter.hoot";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";

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

export const setupWebsiteBuilderOeId = 539;

export const invisibleEl =
    '<div class="s_invisible_el o_snippet_invisible" data-name="Invisible Element" data-invisible="1"></div>';

export function defineWebsiteModels() {
    describe.current.tags("desktop");
    defineMailModels();
    defineModels([Website, IrUiView]);
    onRpc("/website/theme_customize_data_get", () => []);
    onRpc("website", "web_search_read", () => ({
        length: 1,
        records: [
            {
                id: 1,
                default_lang_id: {
                    code: "en_US",
                },
            },
        ],
    }));
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
        loadAssetsFrontendJS = false,
        hasToCreateWebsite = true,
        versionControl = false,
        styleContent,
        headerContent = "",
        beforeWrapwrapContent = "",
        translateMode = false,
        onIframeLoaded = () => {},
        delayReload = async () => {},
    } = {}
) {
    // TODO: fix when the iframe is reloaded and become empty (e.g. discard button)
    if (hasToCreateWebsite) {
        const pyEnv = await startServer();
        pyEnv["website"].create({});
    }
    mockImageRequests();
    registry.category("services").remove("website_edit");
    let editor;
    let editableContent;
    await mountWithCleanup(WebClient);
    let originalIframeLoaded;
    let resolveIframeLoaded = () => {};
    const bodyHTML = `${beforeWrapwrapContent}
        <div id="wrapwrap">${headerContent} <div id="wrap" class="oe_structure oe_empty" ${
        translateMode
            ? ""
            : `data-oe-model="ir.ui.view" data-oe-id="${setupWebsiteBuilderOeId}" data-oe-field="arch"`
    }>${websiteContent}</div></div>`;
    const iframeLoaded = new Promise((resolve) => {
        resolveIframeLoaded = (el) => {
            const iframe = el;
            const styleEl = iframe.contentDocument.createElement("style");
            styleEl.textContent = /*css*/ `* { transition: none !important; } `;
            if (styleContent) {
                styleEl.textContent += styleContent;
            }
            iframe.contentDocument.head.appendChild(styleEl);
            iframe.contentDocument.documentElement.setAttribute(
                "data-main-object",
                "website.page(4,)"
            );
            iframe.contentDocument.body.innerHTML = bodyHTML;
            // we artificially set the is-ready attribute to trick the rest of
            // the code into thinking that the js inside the iframe is properly
            // loaded
            iframe.contentDocument.body.setAttribute("is-ready", "true");

            onIframeLoaded(iframe);
            resolve(el);
        };
    });
    let resolveEditAssetsLoaded = () => {};
    const editAssetsLoaded = new Promise((resolve) => {
        resolveEditAssetsLoaded = () => resolve();
    });

    patchWithCleanup(WebsiteBuilderClientAction.prototype, {
        setIframeLoaded() {
            super.setIframeLoaded();
            this.publicRootReady.resolve();
            originalIframeLoaded = this.iframeLoaded;
            this.iframeLoaded = iframeLoaded;
        },
        async loadAssetsEditBundle() {
            // To instantiate interactions in the iframe test we need to
            // load the edit and frontend bundle in it. The problem is that
            // Hoot does not have control of this iframe and therefore
            // does not mock anything in it (location, rpc, ...). So we don't
            // load the website.assets_edit_frontend bundle.

            if (loadIframeBundles) {
                await loadBundle("website.inside_builder_style", {
                    targetDoc: queryOne("iframe[data-src^='/website/force/1']").contentDocument,
                });
            }
            await resolveEditAssetsLoaded();
        },
        get translation() {
            return translateMode;
        },
        async reloadIframe() {
            await delayReload();
            this.websiteContent.el.contentDocument.body.innerHTML = bodyHTML;
        },
    });
    patchWithCleanup(WebsiteSystrayItem.prototype, {
        get isRestrictedEditor() {
            return true;
        },
        get canEdit() {
            return true;
        },
    });
    await getService("action").doAction({
        name: "Website Builder",
        tag: "website_preview",
        type: "ir.actions.client",
    });

    patchWithCleanup(EditInteractionPlugin.prototype, {
        setup() {
            super.setup();
            // See loadAssetsEditBundle override in WebsiteBuilderClientAction
            // patch.
            this.websiteEditService = {
                update: () => {},
                refresh: () => {},
                stop: () => {},
                stopInteraction: () => {},
            };
        },
    });

    let lastUpdatePromise;
    const waitDomUpdated = async () => {
        // The tick ensures that lastUpdatePromise has correctly been assigned
        await tick();
        await lastUpdatePromise;
        await animationFrame();
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

    if (!versionControl) {
        patchWithCleanup(VersionControlPlugin.prototype, {
            hasAccessToOutdatedEl() {
                return true;
            },
        });
    }

    patchWithCleanupImg();

    const iframe = queryOne("iframe[data-src^='/website/force/1']");
    if (isBrowserFirefox()) {
        await originalIframeLoaded;
    }
    if (loadIframeBundles) {
        await loadBundle("web.assets_frontend", {
            targetDoc: iframe.contentDocument,
            js: loadAssetsFrontendJS,
        });
    }
    resolveIframeLoaded(iframe);
    await animationFrame();
    if (openEditor) {
        await openBuilderSidebar(editAssetsLoaded);
    }
    return {
        getEditor: () => editor,
        getEditableContent: () => editableContent,
        openBuilderSidebar: async () => await openBuilderSidebar(editAssetsLoaded),
        waitDomUpdated,
    };
}

async function openBuilderSidebar(editAssetsLoaded) {
    // The next line allow us to await asynchronous fetches and cache them before it is used
    await Promise.all([getWebsiteSnippets(), loadBundle("website.website_builder_assets")]);

    await click(".o-website-btn-custo-primary");
    await editAssetsLoaded;
    // animationFrame linked to state.isEditing rendering the
    // WebsiteBuilderClientAction.
    await animationFrame();
    // tick needed to wait for the timeout in the WebsiteBuilderClientAction
    // useEffect to be called before advancing time.
    await tick();
    // advanceTime linked to the setTimeout in the WebsiteBuilderClientAction
    // component that removes the systray items.
    await advanceTime(200);
    await animationFrame();
}

export function addPlugin(Plugin) {
    registry.category("website-plugins").add(Plugin.id, Plugin);
    after(() => {
        registry.category("website-plugins").remove(Plugin.id);
    });
}

export function addOption(option) {
    const pluginId = uniqueId("test-option");
    const BaseComponent = option.Component || BaseOptionComponent;
    class Option extends BaseComponent {
        static components = { ...BaseComponent.components, BorderConfigurator };
    }
    const staticProps = { ...option };
    const sequence = staticProps.sequence;
    delete staticProps.Component;
    delete staticProps.sequence;
    Object.assign(Option, staticProps);

    const P = {
        [pluginId]: class extends Plugin {
            static id = pluginId;
            resources = {
                builder_options: sequence ? withSequence(sequence, Option) : Option,
            };
        },
    }[pluginId];
    registry.category("website-plugins").add(pluginId, P);
    after(() => {
        registry.category("website-plugins").remove(pluginId);
    });
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
    const { getEditor, getEditableContent, openBuilderSidebar } = await setupWebsiteBuilder(
        content || "",
        snippetsStructure
    );
    const snippetContent = getSnippetEl(true);

    return { getEditor, getEditableContent, openBuilderSidebar, snippetContent };
}

export async function insertCategorySnippet({ group, snippet } = {}) {
    await contains(
        `.o-snippets-menu #snippet_groups .o_snippet${
            group ? `[data-snippet-group=${group}]` : ""
        } .o_snippet_thumbnail .o_snippet_thumbnail_area`
    ).click();
    await confirmAddSnippet(snippet);
    await waitForEndOfOperation();
}

export async function waitForSnippetDialog() {
    await animationFrame();
    await loadBundle("html_builder.iframe_add_dialog", {
        targetDoc: queryOne("iframe.o_add_snippet_iframe").contentDocument,
        js: false,
    });
    await waitFor(".o_add_snippet_dialog iframe.show.o_add_snippet_iframe");
}

/**
 * @param {string | string[]} snippetName
 */
export async function setupWebsiteBuilderWithSnippet(snippetName, options = {}) {
    mockService("website", {
        get currentWebsite() {
            return {
                metadata: {
                    defaultLangName: "English (US)",
                },
                id: 1,
                default_lang_id: {
                    code: "en_US",
                },
            };
        },
    });

    let html = "";
    const snippetNames = Array.isArray(snippetName) ? snippetName : [snippetName];
    for (const name of snippetNames) {
        html += (await getStructureSnippet(name)).outerHTML;
    }
    return setupWebsiteBuilder(html, {
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
