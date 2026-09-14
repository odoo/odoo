import { describe, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import {
    setupInteractionWhiteList,
    startInteractions,
} from "@web/../tests/public/helpers";
import { browser } from "@web/core/browser/browser";

setupInteractionWhiteList("website.website_page");

describe.current.tags("interaction_dev");

test("a language switch goes through /website/lang with the link's url code", async () => {
    // the selector's links carry `data-url_code` (an underscore key of the
    // dataset); reading a camel-cased key sent every visitor to
    // /website/lang/undefined
    const { core } = await startInteractions(`
        <div id="wrapwrap">
            <div class="js_language_selector">
                <a class="js_change_lang" href="/fr/contact" data-url_code="fr">Français</a>
            </div>
        </div>
    `);
    expect(core.interactions).toHaveLength(1);
    await click(".js_change_lang");
    expect(browser.location.href).toMatch(/\/website\/lang\/fr\?r=%2Ffr%2Fcontact$/);
});
