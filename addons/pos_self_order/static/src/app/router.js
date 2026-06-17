import { Component, computed, xml, useEffect } from "@odoo/owl";
import { escapeRegExp } from "@web/core/utils/strings";
import { zip } from "@web/core/utils/arrays";
import { useService } from "@web/core/utils/hooks";

function parseParams(matches, paramSpecs) {
    return Object.fromEntries(
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
}

export class Router extends Component {
    static props = { slots: Object, pos_config_id: Number };
    static template = xml`<t t-call-slot="{{this.activeSlot}}" t-props="this.slotProps"/>`;

    routeMatch = computed(() => this.matchURL());

    setup() {
        this.router = useService("router");
        this.routes = {};
        const lgPrefixRegex = "^(?:/([a-zA-Z]{2}(?:_[a-zA-Z]{2})?))?"; // optional language code: e.g. fr/ or fr_be/

        for (const [routeName, slot] of Object.entries(this.props.slots)) {
            const route = slot.route;
            const paramStrings = route.match(/\{\w+:\w+\}/g);

            if (!paramStrings) {
                this.routes[routeName] = {
                    route,
                    paramSpecs: [],
                    regex: new RegExp(`${lgPrefixRegex}${route}$`),
                };
                continue;
            }

            const paramSpecs = paramStrings.map((paramString) => {
                const [, type, name] = paramString.match(/(\w+):(\w+)/);
                return { type, name };
            });

            const regex = new RegExp(
                `${lgPrefixRegex}${route
                    .split(/\{\w+:\w+\}/)
                    .map((part) => escapeRegExp(part))
                    .join("([^/]+)")}$`
            );

            this.routes[routeName] = { route, paramSpecs, regex };
        }

        this.router.registerRoutes(this.routes);

        useEffect(() => {
            const routeMatch = this.routeMatch();
            this.router.activeSlot = routeMatch.activeSlot;
            if (!routeMatch.matched) {
                this.router.navigate("default");
            }
        });
    }

    matchURL() {
        const path = this.router.path;

        for (const [routeName, { paramSpecs, regex }] of Object.entries(this.routes)) {
            const match = path.match(regex);
            if (match) {
                const parsedParams = parseParams(match.slice(2), paramSpecs);
                return {
                    activeSlot: routeName,
                    matched: true,
                    slotProps: parsedParams,
                };
            }
        }

        return {
            activeSlot: "default",
            matched: false,
            slotProps: {},
        };
    }

    get activeSlot() {
        return this.routeMatch().activeSlot;
    }

    get slotProps() {
        return this.routeMatch().slotProps;
    }
}
