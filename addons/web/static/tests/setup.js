/** @odoo-module **/

import core from "web.core";
import session from "web.session";
import { browser } from "@web/core/browser/browser";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { legacyProm } from "web.test_legacy";
import { registerCleanup } from "./helpers/cleanup";
import { prepareRegistriesWithCleanup, setTestOdooWithCleanup } from "./helpers/mock_env";

const { whenReady, loadFile } = owl.utils;

owl.config.enableTransitions = false;
owl.QWeb.dev = true;

function forceLocaleAndTimezoneWithCleanup() {
    const originalLocale = luxon.Settings.defaultLocale;
    luxon.Settings.defaultLocale = "en";
    const originalZoneName = luxon.Settings.defaultZoneName;
    luxon.Settings.defaultZoneName = "Europe/Brussels";
    registerCleanup(() => {
        luxon.Settings.defaultLocale = originalLocale;
        luxon.Settings.defaultZoneName = originalZoneName;
    });
}

function patchBrowserWithCleanup() {
    // patch addEventListner to automatically remove listeners bound (via browser.addEventListener)
    // during a test (e.g. during the deployment of a service)
    const originalAddEventListener = browser.addEventListener;
    const originalRemoveEventListener = browser.removeEventListener;
    patchWithCleanup(browser, {
        addEventListener() {
            originalAddEventListener(...arguments);
            registerCleanup(() => {
                originalRemoveEventListener(...arguments);
            });
        },
    });
}

function patchLegacyCoreBus() {
    // patch core.bus.on to automatically remove listners bound on the legacy bus
    // during a test (e.g. during the deployment of a service)
    const originalOn = core.bus.on.bind(core.bus);
    const originalOff = core.bus.off.bind(core.bus);
    patchWithCleanup(core.bus, {
        on() {
            originalOn(...arguments);
            registerCleanup(() => {
                originalOff(...arguments);
            });
        },
    });
}

function patchLegacySession() {
    const userContext = Object.getOwnPropertyDescriptor(session, "user_context");
    registerCleanup(() => {
        Object.defineProperty(session, "user_context", userContext);
    });
}

export async function setupTests() {
    QUnit.testStart(() => {
        setTestOdooWithCleanup();
        prepareRegistriesWithCleanup();
        forceLocaleAndTimezoneWithCleanup();
        patchBrowserWithCleanup();
        patchLegacyCoreBus();
        patchLegacySession();
    });

    const templatesUrl = `/web/webclient/qweb/${new Date().getTime()}?bundle=web.assets_qweb`;
    // TODO replace by `processTemplates` when the legacy system is removed
    let templates = await loadFile(templatesUrl);
    // as we currently have two qweb engines (owl and legacy), owl templates are
    // flagged with attribute `owl="1"`. The following lines removes the 'owl'
    // attribute from the templates, so that it doesn't appear in the DOM. For now,
    // we make the assumption that 'templates' only contains owl templates. We
    // might need at some point to handle the case where we have both owl and
    // legacy templates. At the end, we'll get rid of all this.
    const doc = new DOMParser().parseFromString(templates, "text/xml");
    const owlTemplates = [];
    for (let child of doc.querySelectorAll("templates > [owl]")) {
        child.removeAttribute("owl");
        owlTemplates.push(child.outerHTML);
    }
    templates = `<templates> ${owlTemplates.join("\n")} </templates>`;
    window.__ODOO_TEMPLATES__ = templates;
    await Promise.all([whenReady(), legacyProm]);
}
