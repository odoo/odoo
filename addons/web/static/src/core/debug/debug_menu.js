/** @odoo-module **/

import { useService } from "../service_hook";
import { useEffect } from "../effect_hook";
import { registry } from "../registry";

const debugRegistry = registry.category("debug");

const { Component } = owl;
let debugElementsId = 1;

export class DebugMenu extends Component {
    setup() {
        const globalContext = { env: this.env };
        this.activeCategories = new Set();
        this.contexts = new Map([["global", globalContext]]);
        this.debugService = useService("debug");
        this.hasAccessRights = false;
        // Defined as arrow to be passed as prop
        // @ts-ignore
        this.beforeOpenDropdown = async () => {
            if (!this.hasAccessRights) {
                this.hasAccessRights = true;
                const accessRights = await this.debugService.getAccessRights();
                Object.assign(globalContext, { accessRights });
            }
        };
        this.env.bus.on("DEBUG-MANAGER:ADD-CONTEXT", this, (payload) => {
            const { category, context, inDialog, itemId } = payload;
            if (this.env.inDialog === inDialog) {
                this.contexts.set(itemId, context);
                this.activeCategories.add(category);
            }
        });
        this.env.bus.on("DEBUG-MANAGER:REMOVE-CONTEXT", this, (payload) => {
            const { category, inDialog, itemId } = payload;
            if (this.env.inDialog === inDialog) {
                this.contexts.delete(itemId);
                this.activeCategories.delete(category);
            }
        });
    }

    getElements() {
        const factories = [];
        const context = Object.assign({}, ...this.contexts.values());
        // If not in dialog => gets root (generic) factories
        if (!this.env.inDialog) {
            factories.push(...debugRegistry.getAll());
        }
        // Retrieves the active categories factories
        for (const category of this.activeCategories) {
            factories.push(...debugRegistry.category(category).getAll());
        }
        // Builds, filters and sorts all items
        return factories
            .map((factory) => factory(context))
            .filter(Boolean)
            .sort((x, y) => {
                const xSeq = x.sequence ? x.sequence : 1000;
                const ySeq = y.sequence ? y.sequence : 1000;
                return xSeq - ySeq;
            });
    }

    onDropdownItemSelected(ev) {
        // items of type "component" don't necessarily have a payload/callback
        if (ev.detail.payload && ev.detail.payload.callback) {
            ev.detail.payload.callback();
        }
    }

    onClickOnTagA(ev) {
        if (!ev.ctrlKey) {
            ev.preventDefault();
        }
    }
}

DebugMenu.template = "web.DebugMenu";

export function useDebugMenu(category, context = {}) {
    const component = Component.current;
    const env = component.env;
    const payload = {
        category,
        context,
        inDialog: env.inDialog,
        itemId: debugElementsId++,
    };
    useEffect(
        () => {
            env.bus.trigger("DEBUG-MANAGER:ADD-CONTEXT", payload);
            return () => env.bus.trigger("DEBUG-MANAGER:REMOVE-CONTEXT", payload);
        },
        () => []
    );
}
