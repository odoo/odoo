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
        this.historyPage = "";
        this.activeSlot = null;
        window.addEventListener("popstate", (event) => {
            this.path = window.location.pathname;
        });
    }

    addTableIdentifier(table) {
        const url = new URL(browser.location.href);
        url.searchParams.set("table_identifier", table.identifier);
        history.replaceState({}, "", url);
    }

    getTableIdentifier() {
        const url = new URL(browser.location.href);
        return url.searchParams.get("table_identifier");
    }

    back() {
        if (!this.historyPage.length) {
            // We use the browser history, so if the user arrives on a page with a back button from a link,
            // we don't know the previous page, so we send them back to the beginning of the feed.
            this.navigate("default");
            return;
        }

        history.back();
        this.path = window.location.pathname;
        this.historyPage = window.location.pathname;
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

        url.pathname = route.replace(
            /\{\w+:(\w+)\}/g,
            (match, paramName) => routeParams[paramName]
        );

        history.pushState({}, "", url);
        this.path = window.location.pathname;
        this.historyPage = this.path;
    }

    registerRoutes(routes) {
        Object.assign(this.registeredRoutes, routes);
    }

    // If the url isn't a valid URL, we assume it's a relative path
    customLink(link) {
        let url = "";

        try {
            url = new URL(link.url);
            window.open(url);
        } catch {
            url = new URL(browser.location.href);
            url.pathname = link.url;

            history.pushState({}, "", url);
            this.path = window.location.pathname;
            this.historyPage = this.path;
        }
    }
}

export const SelfOrderRouterService = {
    dependencies: SelfOrderRouter.serviceDependencies,
    async start(env, deps) {
        return new SelfOrderRouter(env, deps);
    },
};

registry.category("services").add("router", SelfOrderRouterService);
