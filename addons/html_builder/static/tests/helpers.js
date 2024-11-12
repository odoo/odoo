import {
    mountWithCleanup,
    defineModels,
    models,
    patchWithCleanup,
    getService,
} from "@web/../tests/web_test_helpers";
import { defineMailModels, startServer } from "@mail/../tests/mail_test_helpers";
import { advanceTime, animationFrame, click, queryOne } from "@odoo/hoot-dom";
import { getWebsiteSnippets } from "./snippets_getter.hoot";
import { SnippetsMenu } from "@html_builder/builder/snippets_menu";
import { WebClient } from "@web/webclient/webclient";
import { loadBundle } from "@web/core/assets";

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

export function defineWebsiteModels() {
    defineMailModels();
    defineModels([Website, IrUiView]);
}

export async function setupWebsiteBuilder(websiteContent, { snippets } = {}) {
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
