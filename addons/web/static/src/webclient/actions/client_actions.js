/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { routeToUrl } from "@web/core/browser/router_service";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { escape, sprintf } from "@web/core/utils/strings";

import { Component, onMounted, xml } from "@odoo/owl";

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
    const message = owl.markup(sprintf(escape(params.message), ...links));
    env.services.notification.add(message, options);
    return params.next;
}

registry.category("actions").add("display_notification", displayNotificationAction);

class InvalidAction extends Component {
    setup() {
        this.notification = useService("notification");
        onMounted(this.onMounted);
    }

    onMounted() {
        const message = sprintf(
            this.env._t("No action with id '%s' could be found"),
            this.props.actionId
        );
        this.notification.add(message, { type: "danger" });
    }
}
InvalidAction.template = xml`<div class="o_invalid_action"></div>`;

registry.category("actions").add("invalid_action", InvalidAction);

/**
 * Client action to reload the whole interface.
 * If action.params.menu_id, it opens the given menu entry.
 * If action.params.action_id, it opens the given action.
 * If action.params.wait, reload will wait the server to be reachable before reloading
 */
function reload(env, action) {
    const { menu_id, action_id, wait } = action.params || {};
    const { router } = env.services;
    const route = { ...router.current };

    if (menu_id || action_id) {
        route.hash = {};
        if (menu_id) {
            route.hash.menu_id = menu_id;
        }
        if (action_id) {
            route.hash.action = action_id;
        }
    }

    // We want to force location.assign(...) (in router.redirect(...)) to do a page reload.
    // To do this, we need to make sure that the url is different.
    route.search = { ...route.search };
    if ("reload" in route.search) {
        delete route.search.reload;
    } else {
        route.search.reload = true;
    }
    const url = browser.location.origin + routeToUrl(route);

    env.bus.trigger("CLEAR-CACHES");
    router.redirect(url, wait);
}

registry.category("actions").add("reload", reload);

/**
 * Client action to go back home.
 * If action.params.wait, reload will wait the server to be reachable before reloading
 */
function home(env, action) {
    const { wait } = action.params || {};
    const url = "/" + (browser.location.search || "");
    env.services.router.redirect(url, wait);
    browser.location.reload(url);
}

registry.category("actions").add("home", home);

/**
 * Client action to refresh the session context (making sure
 * HTTP requests will have the right one) then reload the
 * whole interface.
 */
async function reloadContext(env, action) {
    // side-effect of get_session_info is to refresh the session context
    await env.services.rpc("/web/session/get_session_info");
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
        env.services.action.restore(controller.jsId);
    }
}

registry.category("actions").add("soft_reload", softReload);
