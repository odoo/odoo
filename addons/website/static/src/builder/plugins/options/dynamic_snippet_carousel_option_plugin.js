import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import {
    dynamicContentOfDynamicSnippet,
    getSharedSnippetArg,
    setSharedSnippetInnerArg,
} from "./dynamic_snippet_option_plugin";
import { BuilderAction } from "@html_builder/core/builder_action";

export class DynamicSnippetCarouselOptionPlugin extends Plugin {
    static id = "dynamicSnippetCarouselOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            SetCarouselSliderSpeedAction,
        },
    };
}

export class SetCarouselSliderSpeedAction extends BuilderAction {
    static id = "setCarouselSliderSpeed";
    getValue({ editingElement }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(editingElement);
        const carousel_interval = getSharedSnippetArg(dynamicEl, "wrapper_data")?.carousel_interval;
        return carousel_interval === undefined ? undefined : carousel_interval / 1000;
    }
    apply({ editingElement, value }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(editingElement);
        setSharedSnippetInnerArg(dynamicEl, "wrapper_data", "carousel_interval", value * 1000);
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetCarouselOptionPlugin.id, DynamicSnippetCarouselOptionPlugin);
