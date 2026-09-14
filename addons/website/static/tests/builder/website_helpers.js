import {
    confirmAddSnippet,
    getSnippetStructure,
    getSnippetView,
    patchWithCleanupImg,
    waitForEndOfOperation,
} from "@html_builder/../tests/helpers";
import { Builder } from "@html_builder/builder";
import { SetupEditorPlugin } from "@html_builder/core/setup_editor_plugin";
import { BaseOptionComponent, revertPreview } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { defineMailModels, startServer } from "@mail/../tests/mail_test_helpers";
import { after, describe } from "@odoo/hoot";
import {
    advanceTime,
    animationFrame,
    click,
    queryOne,
    tick,
    waitFor,
} from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    getService,
    mockService,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    waitUntilIdle,
} from "@web/../tests/web_test_helpers";
import { loadBundle } from "@web/core/assets";
import { isBrowserFirefox } from "@web/core/browser/feature_detection";
import { registry } from "@web/core/registry";
import { uniqueId } from "@web/core/utils/functions";
import { WebClient } from "@web/webclient/webclient";
import { EditInteractionPlugin } from "@website/builder/plugins/edit_interaction_plugin";
import { WebsiteSessionPlugin } from "@website/builder/plugins/website_session_plugin";
import { WebsiteBuilder } from "@website/builder/website_builder";
import { WebsiteBuilderClientAction } from "@website/client_actions/website_preview/website_builder_action";
import { WebsiteSystrayItem } from "@website/client_actions/website_preview/website_systray_item";

import { mockImageRequests } from "./image_test_helpers.js";
import { getWebsiteSnippets } from "./snippets_getter.hoot.js";
import { getTranslatedElements } from "./translated_elements_getter.hoot.js";

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

export const websiteBuilderModels = [Website, IrUiView];

export const setupWebsiteBuilderOeId = 539;

export const invisibleEl =
    '<div class="s_invisible_el o_snippet_invisible" data-name="Invisible Element" data-invisible="1"></div>';

export function defineWebsiteModels() {
    describe.current.tags("desktop");
    defineMailModels();
    defineModels(websiteBuilderModels);
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

const domParserCache = new Map();
function patchDOMParser() {
    patchWithCleanup(DOMParser.prototype, {
        parseFromString(html, type) {
            if (type !== "text/html") {
                return super.parseFromString(html, type);
            }
            if (domParserCache.has(html)) {
                return domParserCache.get(html).cloneNode(true);
            }
            const res = super.parseFromString(html, type);
            if (res.body?.firstChild?.id === "snippet_groups") {
                domParserCache.set(html, res);
                return res.cloneNode(true);
            }
            return res;
        },
    });
}

export async function setupWebsiteBuilder(
    websiteContent,
    {
        snippets,
        openEditor = true,
        loadIframeBundles = false,
        loadAssetsFrontendJS = false,
        hasToCreateWebsite = true,
        styleContent,
        headerContent = "",
        footerContent = "",
        beforeWrapwrapContent = "",
        translateMode = false,
        onIframeLoaded = () => {},
        delayReload = async () => {},
    } = {},
) {
    if (hasToCreateWebsite) {
        const pyEnv = await startServer();
        pyEnv["website"].create({});
    }
    mockImageRequests();
    const services = registry.category("services");
    if (services.contains("website_edit")) {
        const websiteEditService = services.get("website_edit");
        services.remove("website_edit");
        after(() => services.add("website_edit", websiteEditService, { force: true }));
    }
    let editor;
    let editableContent;
    const comp = await mountWithCleanup(WebClient);
    let originalIframeLoaded;
    let resolveIframeLoaded = async () => {};
    const bodyHTML = `${beforeWrapwrapContent}
        <div id="wrapwrap">${headerContent} <div id="wrap" class="oe_structure oe_empty" ${
            translateMode
                ? ""
                : `data-oe-model="ir.ui.view" data-oe-id="${setupWebsiteBuilderOeId}" data-oe-field="arch"`
        }>${websiteContent}</div> ${footerContent}</div>`;
    const realPage = loadIframeBundles && loadAssetsFrontendJS;
    let publicEnv;
    const iframeLoaded = new Promise((resolve) => {
        resolveIframeLoaded = async (el) => {
            const iframe = el;
            if (realPage) {
                publicEnv = await navigateToRealPage(iframe);
            }
            const styleEl = iframe.contentDocument.createElement("style");
            styleEl.textContent = `* { transition: none !important; } `;
            if (styleContent) {
                styleEl.textContent += styleContent;
            }
            iframe.contentDocument.head.appendChild(styleEl);
            iframe.contentDocument.documentElement.setAttribute(
                "data-main-object",
                "website.page(4,)",
            );
            if (realPage) {
                await installWebsiteContent(
                    iframe.contentDocument,
                    publicEnv,
                    bodyHTML,
                );
            } else {
                iframe.contentDocument.body.innerHTML = bodyHTML;
                iframe.contentDocument.body.setAttribute("is-ready", "true");
            }

            onIframeLoaded(iframe);
            resolve(el);
        };
    });
    let resolveEditAssetsLoaded = () => {};
    const editAssetsLoaded = new Promise((resolve) => {
        resolveEditAssetsLoaded = () => resolve();
    });

    onRpc("/website/get_translated_elements", () => getTranslatedElements());

    patchDOMParser();

    patchWithCleanup(WebsiteBuilderClientAction.prototype, {
        setIframeLoaded() {
            super.setIframeLoaded();
            this.publicRootReady.resolve();
            originalIframeLoaded = this.iframeLoaded;
            this.iframeLoaded = iframeLoaded;
        },
        preparePublicRootReady() {},
        async loadAssetsEditBundle() {
            if (loadIframeBundles) {
                await loadBundle("website.assets_inside_builder_iframe", {
                    targetDoc: queryOne("iframe[data-src^='/website/force/1']")
                        .contentDocument,
                    js: realPage,
                });
            }
            await resolveEditAssetsLoaded();
        },
        get translation() {
            return translateMode;
        },
        async reloadIframe() {
            await delayReload();
            const doc = this.websiteContent.el.contentDocument;
            if (realPage) {
                await installWebsiteContent(doc, publicEnv, bodyHTML);
            } else {
                doc.body.innerHTML = bodyHTML;
            }
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
    if (snippets) {
        // the action preloads the snippets as soon as it mounts
        patchWithCleanup(IrUiView.prototype, {
            render_public_asset: () => getSnippetView(snippets),
        });
    }
    await getService("action").doAction({
        name: "Website Builder",
        tag: "website_preview",
        type: "ir.actions.client",
    });

    patchWithCleanup(EditInteractionPlugin.prototype, {
        setup() {
            super.setup();
            this.websiteEditService = {
                update: () => {},
                refresh: () => {},
                stop: () => {},
                stopInteraction: () => {},
            };
        },
    });

    let lastUpdatePromise;
    const waitSidebarUpdated = async () => {
        await revertPreview(editor);
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
            editor = this.editor;
        },
    });

    patchWithCleanup(SetupEditorPlugin.prototype, {
        setup() {
            super.setup();
            editableContent = this.getEditableElements(
                '.oe_structure.oe_empty, [data-oe-type="html"]',
            )[0];
        },
    });

    patchWithCleanup(WebsiteSessionPlugin.prototype, {
        getSession() {
            return {};
        },
    });

    patchWithCleanupImg();

    const iframe = queryOne("iframe[data-src^='/website/force/1']");
    if (isBrowserFirefox()) {
        await originalIframeLoaded;
    }
    if (loadIframeBundles && !realPage) {
        await loadBundle("web.assets_frontend", {
            targetDoc: iframe.contentDocument,
            js: false,
        });
    }
    await resolveIframeLoaded(iframe);
    await animationFrame();
    if (openEditor) {
        await openBuilderSidebar(editAssetsLoaded, comp.__owl__.app);
    }
    return {
        getEditor: () => editor,
        getEditableContent: () => editableContent,
        openBuilderSidebar: async () =>
            await openBuilderSidebar(editAssetsLoaded, comp.__owl__.app),
        waitSidebarUpdated,
    };
}

// A page is more than its JS: the bootstrap, the templates and the bridge
// registrations only exist on a server-rendered document, so a test that
// wants the frontend running in the iframe gets the real page the action
// would navigate to, and swaps its content for the test's.
function navigateToRealPage(iframe) {
    const ready = new Promise((resolve, reject) => {
        iframe.addEventListener(
            "load",
            () => {
                const win = iframe.contentWindow;
                win.addEventListener(
                    "PUBLIC-ROOT-READY",
                    (ev) => resolve(ev.detail.env),
                    { once: true },
                );
                setTimeout(
                    () =>
                        reject(
                            new Error(`the public root of ${iframe.src} never booted`),
                        ),
                    10000,
                );
            },
            { once: true },
        );
    });
    iframe.src = iframe.dataset.src;
    return ready;
}

async function installWebsiteContent(doc, publicEnv, bodyHTML) {
    const interactions = publicEnv.services["public.interactions"];
    interactions.stopInteractions();
    const template = doc.createElement("template");
    template.innerHTML = bodyHTML;
    const nodes = [...template.content.childNodes].filter(
        (node) => node.nodeType === Node.ELEMENT_NODE || node.textContent.trim(),
    );
    const wrapwrap = nodes.find((node) => node.id === "wrapwrap");
    doc.getElementById("wrapwrap").replaceWith(wrapwrap);
    for (const node of nodes) {
        if (node !== wrapwrap) {
            doc.body.insertBefore(node, wrapwrap);
        }
    }
    await interactions.startInteractions();
}

async function openBuilderSidebar(editAssetsLoaded, app) {
    await Promise.all([
        getWebsiteSnippets(),
        loadBundle("website.website_builder_assets"),
        loadBundle("html_editor.assets_image_cropper"),
    ]);

    await click(".o-website-btn-custo-primary");
    await editAssetsLoaded;
    await animationFrame();
    await tick();
    await advanceTime(200);
    await animationFrame();
    await waitFor(".o_builder_sidebar_open");
    if (app) {
        await waitUntilIdle([app]);
    }
}

export function addPlugin(...Plugin) {
    patchWithCleanup(WebsiteBuilder.prototype, {
        get builderProps() {
            const props = super.builderProps;
            return { ...props, Plugins: [...props.Plugins, ...Plugin] };
        },
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
    addPlugin(P);
}

export function addActionOption(actions = {}) {
    const pluginId = uniqueId("test-action-plugin");
    class P extends Plugin {
        static id = pluginId;
        resources = {
            builder_actions: actions,
        };
    }
    addPlugin(P);
}

export function addDropZoneSelector(selector) {
    const pluginId = uniqueId("test-dropzone-selector");

    class P extends Plugin {
        static id = pluginId;
        resources = {
            dropzone_selector: [selector],
        };
    }
    addPlugin(P);
}

export async function setupWebsiteBuilderWithDummySnippet(content) {
    const getSnippetEl = (withColoredLevelClass = false) => {
        const className = withColoredLevelClass ? "s_test o_colored_level" : "s_test";
        return `<section class="${className}" data-snippet="s_test" data-name="Test">
            <div class="test_a"></div>
        </section>`;
    };
    const snippetsDescription = () => [
        { name: "Test", groupName: "a", content: getSnippetEl() },
    ];
    const snippetsStructure = {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: snippetsDescription().map((snippetDesc) =>
                getSnippetStructure(snippetDesc),
            ),
        },
    };
    const { getEditor, getEditableContent, openBuilderSidebar } =
        await setupWebsiteBuilder(content || "", snippetsStructure);
    const snippetContent = getSnippetEl(true);

    return { getEditor, getEditableContent, openBuilderSidebar, snippetContent };
}

export async function insertCategorySnippet({ group, snippet } = {}) {
    await contains(
        `.o-snippets-menu #snippet_groups .o_snippet${
            group ? `[data-snippet-group=${group}]` : ""
        } .o_snippet_thumbnail .o_snippet_thumbnail_area`,
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
    patchDOMParser();
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
    const processors = registry.category("html_builder.snippetsPreprocessor").getAll();
    for (const processor of Object.values(processors)) {
        processor("website.snippets", snippetsDocument);
    }
    const snippetEl = snippetsDocument.querySelector(
        `[data-snippet=${snippetName}]:not([data-snippet] [data-snippet])`,
    );
    const el = snippetEl.cloneNode(true);
    el.dataset.name = snippetEl.parentElement.getAttribute("name");
    return el;
}

export async function insertStructureSnippet(editor, snippetName) {
    const snippetEl = await getStructureSnippet(snippetName);
    const parentEl = editor.editable.querySelector("#wrap") || editor.editable;
    parentEl.append(snippetEl);
    editor.shared.history.addStep();
}
