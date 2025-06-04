import { PortalOption, PortalCardVisibilityOption } from "./portal_option";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { StyleAction } from "@html_builder/core/core_builder_action_plugin";
import { BuilderAction } from "@html_builder/core/builder_action";

/**
 * PortalOptionPlugin
 *
 * Registers portal-related builder options and actions for the Website Builder.
 * - Adds PortalOption and PortalCardVisibilityOption to the options panel.
 * - Registers SetStylePortalCardAction and CardVisibilityOptionAction actions.
 *
 * @extends Plugin
 */
class PortalOptionPlugin extends Plugin {
    static id = "portalOption";
    static dependencies = ["customizeWebsite"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [
            withSequence(1, PortalOption),
            withSequence(2, PortalCardVisibilityOption),
        ],
        builder_actions: {
            SetStylePortalCardAction,
            CardVisibilityOptionAction,
        },
        immutable_link_selectors: [".o_portal_index_card > *"],
    };
}

/**
 * SetStylePortalCardAction
 *
 * This action is executed when the user changes the style of the portal card
 * (border style, border radius, border width, border color) from the builder panel.
 */
class SetStylePortalCardAction extends StyleAction {
    static id = "setStylePortalCard";
    static dependencies = ["customizeWebsite", "color"];

    setup() {
        this.preview = false;
        this.dependencies.customizeWebsite.withCustomHistory(this);
    }
    /**
     * Applies the specified style to portal cards.
     *
     * @param {Object} params - Contains mainParam with the CSS property name
     * @param {string} value - The value to apply for the style property
     *
     */
    async apply({ params, value }) {
        const styleName = params.mainParam;
        const variableMap = {
            "border-style": "portal-card-border-style",
            "border-radius": "portal-card-border-radius",
            "border-width": "portal-card-border-width",
            "border-color": "portal-card-border-color",
        };

        if (styleName in variableMap) {
            if (styleName === "border-color") {
                return this.dependencies.customizeWebsite.customizeWebsiteColors({
                    [variableMap[styleName]]: value,
                });
            }
            return this.dependencies.customizeWebsite.customizeWebsiteVariables({
                [variableMap[styleName]]: value,
            });
        }
    }
}

/**
 * CardVisibilityOptionAction
 *
 * This action is triggered when the user enables/disables the visibility
 * of a portal entry card from the portal builder sidebar.
 */
class CardVisibilityOptionAction extends BuilderAction {
    static id = "cardVisibilityOption";

    setup() {
        this.reload = {};
    }
    apply({ value }) {
        this.toggleCardVisibility(value, true);
    }
    clean({ value }) {
        this.toggleCardVisibility(value, false);
    }
    async toggleCardVisibility(value, show) {
        await this.services.orm.write("portal.entry", [parseInt(value)], {
            show_in_portal: show,
        });
    }
    isApplied({ editingElement, value }) {
        return !!editingElement.querySelector(`[data-id='${value}']`);
    }
}

registry.category("website-plugins").add(PortalOptionPlugin.id, PortalOptionPlugin);
