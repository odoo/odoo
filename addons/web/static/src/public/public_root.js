import { whenReady } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { jsToPyLocale, pyToJsLocale } from "@web/core/l10n/utils";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { mountComponent } from "@web/env";
import lazyloader from "@web/public/lazyloader";

const { Settings } = luxon;

// Load localizations outside the PublicRoot to not wait for DOM ready (but
// wait for them in PublicRoot)
function getLang() {
    const html = document.documentElement;
    return jsToPyLocale(html.getAttribute("lang")) || "en_US";
}
const lang = cookie.get("frontend_lang") || getLang(); // FIXME the cookie value should maybe be in the ctx?

/**
 * This widget is important, because the tour manager needs a root widget in
 * order to work. The root widget must be a service provider with the ajax
 * service, so that the tour manager can let the server know when tours have
 * been consumed.
 */
export async function createPublicRoot() {
    await lazyloader.allScriptsLoaded;
    await whenReady();
    const { env, root } = await mountComponent(MainComponentsContainer, document.body, {
        name: "Odoo public",
    });
    env.services["public.interactions"].isReady.then(() => {
        document.body.setAttribute("is-ready", "true");
    });

    const locale = pyToJsLocale(lang) || browser.navigator.language;
    Settings.defaultLocale = locale;

    return root;
}
