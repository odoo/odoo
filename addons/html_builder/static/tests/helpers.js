import { SnippetsMenu } from "@html_builder/builder/snippets_menu";
import { setContent } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { defineMailModels, startServer } from "@mail/../tests/mail_test_helpers";
import { after } from "@odoo/hoot";
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

export const wrapExample = `<div id="wrap" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch">${exampleWebsiteContent}</div>`;

export function defineWebsiteModels() {
    defineMailModels();
    defineModels([Website, IrUiView]);
}

export async function setupWebsiteBuilder(websiteContent, { snippets, openEditor = true } = {}) {
    const pyEnv = await startServer();
    pyEnv["website"].create({});
    let editor;
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        name: "Website Builder",
        tag: "egg_website_preview",
        type: "ir.actions.client",
    });

    patchWithCleanup(SnippetsMenu.prototype, {
        setup() {
            super.setup();
            editor = this.editor;
        },
    });

    if (snippets) {
        patchWithCleanup(IrUiView.prototype, {
            render_public_asset: () => {
                return getSnippetView(snippets);
            },
        });
    }

    const iframe = queryOne("iframe[data-src='/website/force/1']");
    iframe.contentDocument.body.innerHTML = `<div id="wrapwrap">${websiteContent}</div>`;
    if (openEditor) {
        await openSnippetsMenu();
    }
    return { getEditor: () => editor };
}

export async function openSnippetsMenu() {
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

const actionsRegistry = registry.category("website-builder-actions");

export function addOption({ selector, template, Component, sequence }) {
    const optionId = uniqueId("test-option");
    registry.category("sidebar-element-option").add(optionId, {
        OptionComponent: Component,
        template,
        selector,
        sequence,
    });
    after(() => {
        registry.category("sidebar-element-option").remove(optionId);
    });
}

export function addActionOption(actions = {}) {
    for (const [name, action] of Object.entries(actions)) {
        actionsRegistry.add(name, action);
    }
    after(() => {
        for (const [name] of Object.entries(actions)) {
            actionsRegistry.remove(name);
        }
    });
}

export async function modifyText(editor) {
    setContent(editor.editable, getEditable('<h1 class="title">H[]ello</h1>'));
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
