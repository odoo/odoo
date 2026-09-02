import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { location } from "@web/core/browser/browser";
import { escapeRegExp } from "@web/core/utils/strings";
import { zip } from "@web/core/utils/arrays";
import { signal, Plugin, computed } from "@odoo/owl";

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

export class PosRouterPlugin extends Plugin {
    registeredScreens = signal.Map(new Map());
    currentScreen = signal(null);
    currentScreenParams = signal({});
    historyPage = signal(null);
    page = computed(() => {
        const posPage = registry.category("pos_pages").get(this.currentScreen());
        return {
            name: posPage.name,
            component: posPage.component,
            params: this.currentScreenParams(),
        };
    });

    setup(env) {
        this.popStateCallback = null;
        window.addEventListener("popstate", (event) => {
            this.matchURL();
            this.popStateCallback && this.popStateCallback(event);
        });

        this.initRegisteredRoutes();
        this.matchURL();
    }

    initRegisteredRoutes() {
        const pages = registry.category("pos_pages").getAll();
        for (const { name, route } of pages) {
            const paramStrings = route.match(/\{\w+:\w+\}/g);

            if (!paramStrings) {
                this.registeredScreens().set(name, {
                    route,
                    paramSpecs: [],
                    regex: new RegExp(`^${route}$`),
                });
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

            this.registeredScreens().set(name, { route, regex, paramSpecs });
        }
    }

    back() {
        if (!this.historyPage() || !this.historyPage().length) {
            this.navigate("LoginScreen", {
                configId: odoo.pos_config_id,
            });
            return;
        }

        history.back();
    }

    close() {
        window.location.href = `/pos/ui/${odoo.pos_config_id}`;
    }

    matchURL(props = {}) {
        const path = window.location.pathname;
        for (const [routeName, { regex, paramSpecs }] of this.registeredScreens()) {
            const match = path.match(regex);
            if (match) {
                const parsedParams = parseParams(match.slice(1), paramSpecs);
                this.currentScreen.set(routeName);
                this.currentScreenParams.set({ ...props, ...parsedParams });
                return;
            }
        }

        // In case no route matches, we default to the LoginScreen
        this.currentScreen.set("LoginScreen");
    }

    getRoute(routeName) {
        try {
            const { route } = this.registeredScreens().get(routeName);
            return route;
        } catch {
            const { route } = this.registeredScreens().get("ProductScreen");
            return route;
        }
    }

    navigate(routeName, routeParams = {}) {
        const route = this.getRoute(routeName);
        const url = new URL(location.href);

        url.pathname = route.replace(
            /\{\w+:(\w+)\}/g,
            (match, paramName) => routeParams[paramName]
        );

        history.pushState({}, "", url);
        this.historyPage.set(window.location.pathname);
        this.matchURL(routeParams);
    }

    registerRoutes(routes) {
        Object.entries(routes).forEach(([key, value]) => {
            this.registeredScreens().set(key, value);
        });
    }
}

services.add(PosRouterPlugin);
