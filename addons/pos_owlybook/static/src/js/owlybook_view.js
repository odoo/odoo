/** @odoo-module */

import { Sidebar } from "./sidebar/sidebar";
import { Canvas } from "./canvas/canvas";
import { Component, onMounted } from "@odoo/owl";
import { setupStories } from "./stories";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { router, routerBus } from "@web/core/browser/router";
import { Notebook } from "@web/core/notebook/notebook";

import { ComponentProperties } from "./bottom_panel/component_properties/component_properties";
import { Events } from "./bottom_panel/events/events";

export class OwlybookView extends Component {
    static template = "pos_owlybook.OwlybookView";
    static components = {
        Sidebar,
        Canvas,
        MainComponentsContainer,
        Notebook,
        ComponentProperties,
        Events,
    };

    setup() {
        this.stories = setupStories(router);
        onMounted(this.onMounted);
        useBus(routerBus, "ROUTE_CHANGE", this.setStoryFromUrl);
        this.hideSidebar = router.current?.hideSidebar;
    }

    onMounted() {
        this.setStoryFromUrl();
    }

    setStoryFromUrl() {
        const state = router.current || {};
        if (state.title && state.folder && state.module) {
            this.stories.setActive(this.stories.getStoryByDescription(state));
        }
    }
}
