import { registry } from "@web/core/registry";
import { Reactive } from "@web/core/utils/reactive";
import { browser } from "@web/core/browser/browser";
import { escapeRegExp } from "@web/core/utils/strings";
import { zip } from "@web/core/utils/arrays";

const parseParams = (matches, paramSpecs) =>
    Object.fromEntries(
        zip(matches, paramSpecs).map(([match, paramSpec]) => {
            const { type, name } = paramSpec;
            switch (type) {
                case "int":
                    return [name, parseInt(match)];
                case "string":
                    return [name, match];
                default:
                    throw new Error(`Unknown type ${type}`);
            }
        })
    );

export class PosRouter extends Reactive {
    static serviceDependencies = [];

    constructor(...args) {
        super(...args);
        this.setup(...args);
    }

    setup(env) {
        this.path = window.location.pathname;
        this.registeredRoutes = {};
        this.popStateCallback = null;
        this.state = {
            params: {},
            current: null,
            previous: null,
        };

        window.addEventListener("popstate", (event) => {
            this.path = window.location.pathname;
            this.matchURL();
            this.popStateCallback && this.popStateCallback(event);
        });

        this.initRegisteredRoutes();
        this.matchURL();
    }

    get page() {
        const page = registry.category("pos_pages").get(this.state.current);
        const params = this.state.params;
        return {
            name: page.name,
            component: page.component,
            params,
        };
    }

    initRegisteredRoutes() {
        const pages = registry.category("pos_pages").getAll();
        for (const { name, route } of pages) {
            const paramStrings = route.match(/\{\w+:\w+\}/g);

            if (!paramStrings) {
                this.registeredRoutes[name] = {
                    route,
                    paramSpecs: [],
                    regex: new RegExp(`^${route}$`),
                };
                continue;
            }

            const paramSpecs = paramStrings.map((paramString) => {
                const [, type, name] = paramString.match(/(\w+):(\w+)/);
                return { type, name };
            });

            const regex = new RegExp(
                `^${route
                    .split(/\{\w+:\w+\}/)
                    .map((part) => escapeRegExp(part))
                    .join("([^/]+)")}$`
            );

            this.registeredRoutes[name] = { route, regex, paramSpecs };
        }
    }

    back() {
        if (!this.historyPage.length) {
            this.navigate("LoginScreen", {
                configId: odoo.pos_config_id,
            });
            return;
        }

        history.back();
        this.path = window.location.pathname;
        this.state.previous = window.location.pathname;
    }

    close() {
        window.location.href = `/pos/ui/${odoo.pos_config_id}`;
    }

    matchURL(props = {}) {
        const path = this.path;

        for (const [routeName, { regex, paramSpecs }] of Object.entries(this.registeredRoutes)) {
            const match = path.match(regex);
            if (match) {
                const parsedParams = parseParams(match.slice(1), paramSpecs);
                this.state.current = routeName;
                this.state.params = { ...props, ...parsedParams };
                return;
            }
        }

        // In case no route matches, we default to the LoginScreen
        this.state.current = "LoginScreen";
    }

    getRoute(routeName) {
        try {
            const { route } = this.registeredRoutes[routeName];
            return route;
        } catch {
            const { route } = this.registeredRoutes["ProductScreen"];
            return route;
        }
    }

    navigate(routeName, routeParams = {}) {
        const route = this.getRoute(routeName);
        const url = new URL(browser.location.href);

        url.pathname = route.replace(
            /\{\w+:(\w+)\}/g,
            (match, paramName) => routeParams[paramName]
        );

        history.pushState({}, "", url);
        this.path = window.location.pathname;
        this.historyPage = this.path;
        this.matchURL(routeParams);
    }

    registerRoutes(routes) {
        Object.assign(this.registeredRoutes, routes);
    }
}

export const PosRouterService = {
    dependencies: PosRouter.serviceDependencies,
    async start(env, deps) {
        return new PosRouter(env, deps);
    },
};

registry.category("services").add("pos_router", PosRouterService);
