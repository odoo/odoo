// @ts-check

/** @module @web/boot/start - Initializes session data, caches, and mounts the root web client component */

import { Component, whenReady } from "@odoo/owl";
import { hasTouch } from "@web/core/browser/feature_detection";
import { localization } from "@web/core/l10n/localization";
import { rpc } from "@web/core/network/rpc";
import { RPCCache } from "@web/core/network/rpc_cache";
import { mountComponent } from "@web/env";
import { user } from "@web/services/user";
import { session } from "@web/session";

// Chrome iOS wraps some text nodes (like measures, email...)
// with a `<chrome_annotation>` tag, which breaks OWL rendering.
// This meta tag allows to disable this behavior.
const chromeMetaTag = document.createElement("meta");
chromeMetaTag.setAttribute("name", "chrome");
chromeMetaTag.setAttribute("content", "nointentdetection");
document.head.appendChild(chromeMetaTag);

/**
 * Function to start a webclient.
 * It is used both in community and enterprise in main.js.
 * It's meant to be webclient flexible so we can have a subclass of
 * webclient in enterprise with added features.
 *
 * @param {Component} Webclient
 */
export async function startWebClient(Webclient) {
    /** @type {any} */ (odoo).info = {
        db: session.db,
        server_version: session.server_version,
        server_version_info: session.server_version_info,
        isEnterprise: (session.server_version_info ?? []).at(-1) === "e",
    };
    /** @type {any} */ (odoo).isReady = false;

    if (window.isSecureContext && session.browser_cache_secret) {
        rpc.setCache(
            new RPCCache("rpc", session.registry_hash, session.browser_cache_secret),
        );
    }

    await whenReady();
    const app = await mountComponent(Webclient, document.body, {
        name: "Odoo Web Client",
    });
    const env = /** @type {any} */ (app).env;
    /** @type {any} */ (Component).env = env;

    const classList = document.body.classList;
    if (localization.direction === "rtl") {
        classList.add("o_rtl");
    }
    if (user.userId === 1) {
        classList.add("o_is_superuser");
    }
    if (env.debug) {
        classList.add("o_debug");
    }
    if (hasTouch()) {
        classList.add("o_touch_device");
    }
    // delete odoo.debug; // FIXME: some legacy code rely on this
    /** @type {any} */ (odoo).isReady = true;
}
