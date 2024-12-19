import { BuilderSidebar } from "@html_builder/builder/builder_sidebar/builder_sidebar";
import { WebsiteBuilder } from "@html_builder/website_builder_action";
import { setContent } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { defineMailModels, startServer } from "@mail/../tests/mail_test_helpers";
import { after, describe } from "@odoo/hoot";
import { advanceTime, animationFrame, click, queryOne } from "@odoo/hoot-dom";
import {
    defineModels,
    getService,
    models,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { uniqueId } from "@web/core/utils/functions";
import { WebClient } from "@web/webclient/webclient";
import { getWebsiteSnippets } from "./snippets_getter.hoot";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";

class Website extends models.Model {
    _name = "website";
    get_current_website() {
        return "website(1,)";
    }
}

class IrUiView extends models.Model {
    _name = "ir.ui.view";
    render_public_asset() {
        return getWebsiteSnippets();
    }
}

export const exampleWebsiteContent = '<h1 class="title">Hello</h1>';

export const invisiblePopup =
    '<div class="s_popup o_snippet_invisible" data-snippet="s_popup" data-name="Popup" id="sPopup1732546784762" data-invisible="1"></div>';

export const wrapExample = `<div id="wrap" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch">${exampleWebsiteContent}</div>`;

export function defineWebsiteModels() {
    describe.current.tags("desktop");
    defineMailModels();
    defineModels([Website, IrUiView]);
}

export async function setupWebsiteBuilder(
    websiteContent,
    { snippets, openEditor = true, loadIframeBundles = false } = {}
) {
    const pyEnv = await startServer();
    pyEnv["website"].create({});
    let editor;
    await mountWithCleanup(WebClient);
    let resolveIframeLoaded = () => {};
    const iframeLoaded = new Promise((resolve) => {
        resolveIframeLoaded = (el) => {
            resolve(el);
        };
    });
    patchWithCleanup(WebsiteBuilder.prototype, {
        get systrayProps() {
            return {
                onNewPage: this.onNewPage.bind(this),
                onEditPage: this.onEditPage.bind(this),
                iframeLoaded: iframeLoaded,
            };
        },
        get menuProps() {
            return {
                closeEditor: this.reloadIframeAndCloseEditor.bind(this),
                snippetsName: "website.snippets",
                toggleMobile: this.toggleMobile.bind(this),
                isTranslation: !!this.translation,
                iframeLoaded: iframeLoaded,
                overlayRef: this.overlayRef,
                isMobile: this.state.isMobile,
            };
        },
    });
    await getService("action").doAction({
        name: "Website Builder",
        tag: "egg_website_preview",
        type: "ir.actions.client",
    });

    patchWithCleanup(BuilderSidebar.prototype, {
        setup() {
            super.setup();
            editor = this.editor;
        },
    });

    if (snippets) {
        patchWithCleanup(IrUiView.prototype, {
            render_public_asset: () => getSnippetView(snippets),
        });
    }

    const iframe = queryOne("iframe[data-src^='/website/force/1']");
    iframe.contentDocument.body.innerHTML = `<div id="wrapwrap">${websiteContent}</div>`;
    if (loadIframeBundles) {
        loadBundle("html_builder.inside_builder_style", {
            targetDoc: iframe.contentDocument,
        });
        loadBundle("web.assets_frontend", {
            targetDoc: iframe.contentDocument,
            js: false,
        });
    }
    resolveIframeLoaded(iframe);
    await animationFrame();
    if (openEditor) {
        await openBuilderSidebar();
    }
    return { getEditor: () => editor };
}

export async function openBuilderSidebar() {
    // The next line allow us to await asynchronous fetches and cache them before it is used
    await Promise.all([getWebsiteSnippets(), loadBundle("website.assets_builder")]);

    await click(".o-website-btn-custo-primary");
    // linked to the setTimeout in the WebsiteBuilder component
    await advanceTime(200);
    await animationFrame();
}

export function getEditable(inWrap) {
    return `<div id="wrap" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch">${inWrap}</div>`;
}

export function addOption({ selector, exclude, template, Component, sequence }) {
    const pluginId = uniqueId("test-option");
    const Class = makeOptionPlugin({
        pluginId,
        OptionComponent: Component,
        template,
        selector,
        exclude,
        sequence,
    });
    registry.category("website-plugins").add(pluginId, Class);
    after(() => {
        registry.category("website-plugins").remove(pluginId);
    });
}
function makeOptionPlugin({ pluginId, template, selector, exclude, sequence, OptionComponent }) {
    const option = {
        OptionComponent,
        template,
        selector,
        exclude,
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

export async function modifyText(editor) {
    setContent(editor.editable, getEditable('<h1 class="title">H[]ello</h1>'));
    editor.shared.history.addStep();
    await insertText(editor, "1");
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
