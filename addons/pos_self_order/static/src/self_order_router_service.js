/** @odoo-module */

import { registry } from "@web/core/registry";
import { Reactive } from "@web/core/utils/reactive";
import { browser } from "@web/core/browser/browser";

export class SelfOrderRouter extends Reactive {
    static serviceDependencies = [];

    constructor(...args) {
        super(...args);
        this.setup(...args);
    }

    setup(env) {
        this.path = window.location.pathname;
        this.registeredRoutes = {};

        window.addEventListener("popstate", (event) => {
            this.path = window.location.pathname;
        });
    }

    back() {
        history.back();
        this.path = window.location.pathname;
    }

    /**
     * Navigate to the given relative route.
     * We use the history API to navigate to it.
     * (this means that we don't make additional requests to the server)
     * @param {string} route
     */
    navigate(routeName, routeParams = {}) {
        const { route } = this.registeredRoutes[routeName];
        const url = new URL(browser.location.href);

        url.pathname = route.replace(/\{\w+:(\w+)\}/g, (match, paramName) => {
            return routeParams[paramName];
        });

        history.pushState({}, "", url);
        this.path = window.location.pathname;
    }

    registerRoutes(routes) {
        Object.assign(this.registeredRoutes, routes);
    }

    customLink(link) {
        const url = new URL(browser.location.href);
        url.pathname = link.url;

        history.pushState({}, "", url);
        this.path = window.location.pathname;
    }
}

export const SelfOrderRouterService = {
    dependencies: SelfOrderRouter.serviceDependencies,
    async start(env, deps) {
        return new SelfOrderRouter(env, deps);
    },
};

registry.category("services").add("router", SelfOrderRouterService);
