import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { escape, sprintf } from "@web/core/utils/strings";

import { markup } from "@odoo/owl";

export function displayNotificationAction(env, action) {
    const params = action.params || {};
    const options = {
        className: params.className || "",
        sticky: params.sticky || false,
        title: params.title,
        type: params.type || "info",
    };
    const links = (params.links || []).map((link) => {
        return `<a href="${escape(link.url)}" target="_blank">${escape(link.label)}</a>`;
    });
    const message = markup(sprintf(escape(params.message), ...links));
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

    env.bus.trigger("CLEAR-CACHES");
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
 * Client action to refresh the session context (making sure
 * HTTP requests will have the right one) then reload the
 * whole interface.
 */
async function reloadContext(env, action) {
    // side-effect of get_session_info is to refresh the session context
    await rpc("/web/session/get_session_info");
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
