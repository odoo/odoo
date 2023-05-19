/** @odoo-module */

import { Component, useState, useSubEnv, xml } from "@odoo/owl";
import { escapeRegExp } from "@web/core/utils/strings";
import { browser } from "@web/core/browser/browser";
import { zip } from "@web/core/utils/arrays";
import { useSelfOrder } from "./SelfOrderService";

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
    static template = xml`<t t-slot="{{state.activeSlot}}" t-props="state.slotProps"/>`;
    setup() {
        this.selfOrder = useSelfOrder();
        this.selfOrder.navigate = this.navigate.bind(this);
        useSubEnv({
            navigate: this.navigate.bind(this),
            getCurrentRoute: this.getCurrentRoute.bind(this),
        });
        this.state = useState({
            activeSlot: "default",
            slotProps: {},
        });
        // this is needed for the back button to work
        window.addEventListener("popstate", (event) => {
            this.matchURL();
        });
        this.routes = Object.keys(this.props.slots).map((route) => {
            const paramStrings = route.match(/\{\w+:\w+\}/g);
            if (!paramStrings) {
                return { route, paramSpecs: [], regex: new RegExp(`^${route}$`) };
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
            return { route, paramSpecs, regex };
        });
        this.matchURL();
    }

    matchURL() {
        const path = browser.location.pathname;
        for (const { route, paramSpecs, regex } of this.routes) {
            const match = path.match(regex);
            if (match) {
                const parsedParams = parseParams(match.slice(1), paramSpecs);
                this.state.activeSlot = route;
                this.state.slotProps = parsedParams;
                return;
            }
        }
        this.state.activeSlot = "default";
        this.state.slotProps = {};
    }
    /**
     * Navigate to the given relative route.
     * We use the history API to navigate to it.
     * (this means that we don't make additional requests to the server)
     * @param {string} route
     * @param {number} pos_config_id
     */
    navigate(route, pos_config_id = this.props.pos_config_id) {
        const url = new URL(browser.location.href);
        url.pathname = `menu/${pos_config_id}${route}`;
        history.pushState({}, "", url);
        this.matchURL();
    }
    /**
     * @returns {string[]}
     */
    getCurrentRoute() {
        const baseLength = "/menu/{string:pos_name}".split("/").length;
        // The base part of the route is there on all routes, so it
        // makes no sense to have it in the return
        return this.state.activeSlot.split("/").splice(baseLength);
    }
}
