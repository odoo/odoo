import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { htmlSprintf } from "@web/core/utils/html";

import { markup } from "@odoo/owl";

export function displayNotificationAction(env, action) {
    const params = action.params || {};
    const options = {
        className: params.className || "",
        sticky: params.sticky || false,
        title: params.title,
        type: params.type || "info",
    };
    const links = (params.links || []).map(
        (link) => markup`<a href="${link.url}" target="_blank">${link.label}</a>`
    );
    const message = htmlSprintf(params.message, ...links);
    env.services.notification.add(message, options);
    return params.next;
}

registry.category("actions").add("display_notification", displayNotificationAction);

/**
 * Client action to reload the whole interface.
 * If action.params.menu_id, it opens the given menu entry.
 * If action.params.action_id, it opens the given action.
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
 */
async function reloadContext(env, action) {
    reload(env, action);
}

registry.category("actions").add("reload_context", reloadContext);

/**
 * Client action to restore the current controller
 * Serves as a trigger to reload the interface without a full browser reload
 */
async function softReload(env, action) {
    const controller = env.services.action.currentController;
    if (controller) {
        await env.services.action.restore(controller.jsId);
    }
}

registry.category("actions").add("soft_reload", softReload);
