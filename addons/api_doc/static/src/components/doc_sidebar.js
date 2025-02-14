import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { simplifyString } from "@api_doc/utils/doc_model_search";

export class DocSidebar extends Component {
    static template = "web.DocSidebar";

    static components = {};
    static props = {};

    setup() {
        this.containerRef = useRef("containerRef");
        this.modelStore = useState(this.env.modelStore);
        this.state = useState({
            collapseAddons: {},
            searchValue: "",
        });

        useEffect(
            () => {
                this.containerRef.el?.querySelector(":scope .o_active")?.scrollIntoView();
            },
            () => [this.containerRef.el]
        );
    }

    onSearchInput(event) {
        this.state.searchValue = event.target.value;
        this.containerRef.el.scrollTop = 0;
    }

    toggleAddon(addonName) {
        this.state.collapseAddons[addonName] = !this.isCollapsed(addonName);
    }

    isCollapsed(addonName) {
        return this.state.collapseAddons[addonName];
    }

    isActiveItem(model) {
        return (
            this.modelStore.activeModel &&
            model.name === this.modelStore.activeModel.name &&
            model.model == this.modelStore.activeModel.model
        );
    }

    get filteredAddons() {
        const queryStr = simplifyString(this.state.searchValue);

        if (queryStr <= 0) {
            return [...this.modelStore.addons];
        } else {
            const visibleAddons = [];
            for (const addon of this.modelStore.addons) {
                let models = addon.models;
                if (!addon.name.includes(queryStr)) {
                    models = addon.models.filter(
                        (model) =>
                            simplifyString(model.name).includes(queryStr) ||
                            simplifyString(model.model).includes(queryStr)
                    );
                }
                if (models.length > 0) {
                    visibleAddons.push({
                        name: addon.name,
                        models,
                    });
                }
            }
            return visibleAddons;
        }
    }
}
