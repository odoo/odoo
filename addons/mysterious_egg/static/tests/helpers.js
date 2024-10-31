import { mountWithCleanup, defineModels, models, patchWithCleanup, getService } from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { advanceTime, animationFrame, click, queryOne } from "@odoo/hoot-dom";
import { getWebsiteSnippets } from "./snippets_getter.hoot";
import { SnippetsMenu } from "@mysterious_egg/builder/snippets_menu";
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

export async function setupWebsiteBuilder(websiteContent) {
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

    const iframe = queryOne("iframe[data-src='/website/force/1']");
    iframe.contentDocument.body.innerHTML = websiteContent;
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
