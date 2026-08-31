import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { browser } from "@web/core/browser/browser";
import { escapeRegExp } from "@web/core/utils/strings";
import { zip } from "@web/core/utils/arrays";
import { signal, Plugin, computed, usePlugin } from "@odoo/owl";
import { uuidv4, random5Chars } from "@point_of_sale/utils";
import { PosDataPlugin } from "@point_of_sale/app/plugins/pos_data_plugin";

const { DateTime } = luxon;

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
    data = usePlugin(PosDataPlugin);
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

    init({ config }) {
        this.config = config;
    }

    setNextOrderRefs(order) {
        const deviceIdentifier = this.data.device.identifier;
        const number = `${this.data.device.useNext()}`.padStart(6, "0");
        const configId = this.config.id;
        const year2Digits = DateTime.now().year.toString().slice(-2);
        const posReference = `${year2Digits}${deviceIdentifier}-${configId}-${number}`;

        order.pos_reference = posReference;
        order.tracking_number = deviceIdentifier + `${parseInt(number) % 1000}`.padStart(3, "0");
    }

    get defaultPage() {
        let openOrder = this.config.models["pos.order"].find((o) => o.state === "draft");
        if (!openOrder) {
            openOrder = this.config.models["pos.order"].create({
                session_id: this.data.session_id,
                company_id: this.config.company_id,
                config_id: this.config.id,
                access_token: uuidv4(),
                ticket_code: random5Chars(),
                tracking_number: "",
                sequence_number: 0,
                pos_reference: "",
            });
            this.setNextOrderRefs(openOrder);
        }
        return {
            page: "ProductScreen",
            params: {
                orderUuid: openOrder.uuid,
            },
        };
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
        const url = new URL(browser.location.href);

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
