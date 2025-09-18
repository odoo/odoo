// @ts-check

/** @module @web/webclient/actions/client_actions - Built-in client actions (display_notification, soft_reload, reload_context) */

import { markup } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { makeErrorFromResponse, rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { htmlSprintf } from "@web/core/utils/dom/html";
/**
 * Client action to display a notification with optional links.
 *
 * @param {Object} env - the OWL environment
 * @param {Object} action - the action descriptor with params (title, message, type, links, next)
 * @returns {Object | undefined} optional follow-up action
 */
export function displayNotificationAction(env, action) {
    const params = action.params || {};
    const options = {
        className: params.className || "",
        sticky: params.sticky || false,
        title: params.title,
        type: params.type || "info",
    };
    const links = (params.links || []).map(
        (link) => markup`<a href="${link.url}" target="_blank">${link.label}</a>`,
    );
    const message = htmlSprintf(params.message, ...links);
    env.services.notification.add(message, options);
    return params.next;
}

registry.category("actions").add("display_notification", displayNotificationAction);

/**
 * Client action to trigger an Exception on the interface.
 *
 * @param {Object} env
 * @param {Object} action - action with params matching error response shape
 */
function displayException(env, action) {
    throw makeErrorFromResponse(action.params);
}

registry.category("actions").add("display_exception", displayException);

/**
 * Client action to reload the whole interface.
 * If action.params.menu_id, it opens the given menu entry.
 * If action.params.action_id, it opens the given action.
 *
 * @param {Object} env
 * @param {Object} action
 */
function reload(env, action) {
    const { menu_id, action_id } = action.params || {};
    let route = { ...router.current };

    if (menu_id || action_id) {
        route = {};
        if (menu_id) {
            route.menu_id = menu_id;
        }
        if (action_id) {
            route.action = action_id;
        }
    }

    router.pushState(route, { replace: true, reload: true });
}

registry.category("actions").add("reload", reload);

/**
 * Client action to go back home.
 */
async function home() {
    await new Promise((resolve) => {
        const waitForServer = (delay) => {
            browser.setTimeout(async () => {
                rpc("/web/webclient/version_info", {})
                    .then(resolve)
                    .catch(() => waitForServer(250));
            }, delay);
        };
        waitForServer(1000);
    });
    const url = "/" + (browser.location.search || "");
    browser.location.assign(url);
}

registry.category("actions").add("home", home);

/**
 * Client action to refresh the session context (making sure HTTP requests will
 * have the right one). It simply reloads the page.
 *
 * @param {Object} env
 * @param {Object} action
 */
async function reloadContext(env, action) {
    reload(env, action);
}

registry.category("actions").add("reload_context", reloadContext);

/**
 * Client action to restore the current controller.
 * Serves as a trigger to reload the interface without a full browser reload.
 *
 * @param {Object} env
 * @param {Object} action
 */
async function softReload(env, action) {
    const controller = env.services.action.currentController;
    if (controller) {
        await env.services.action.restore(controller.jsId);
    }
}

registry.category("actions").add("soft_reload", softReload);
