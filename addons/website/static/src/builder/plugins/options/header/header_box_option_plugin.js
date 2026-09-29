import { BuilderAction } from "@html_builder/core/builder_action";
import {
    getCurrentShadow,
    getDefaultShadow,
    SetShadowModeAction,
    SetShadowStyleAction,
    shadowToString,
} from "@html_builder/plugins/shadow_option_plugin";
import { StyleAction } from "@html_builder/core/core_builder_action_plugin";
import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";

export class HeaderBoxOptionPlugin extends Plugin {
    static id = "HeaderBoxOptionPlugin";
    static dependencies = ["customizeWebsite"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            StyleActionHeaderAction,
            SetShadowClassHeaderAction,
            SetShadowModeHeaderAction,
            SetShadowStyleHeaderAction,
        },
    };
}

export class StyleActionHeaderAction extends StyleAction {
    static id = "styleActionHeader";
    static dependencies = ["customizeWebsite", "color"];
    getValue(...args) {
        const { params } = args[0];
        const value = super.getValue(...args);
        if (params.mainParam === "border-width") {
            return value.replace(/(^|\s)0px/gi, "").trim() || value;
        }
        return value;
    }
    apply({ params: { mainParam: styleName }, value }) {
        const customizeWebsite = this.dependencies.customizeWebsite;
        if (styleName === "border-color") {
            customizeWebsite.previewColorVariable("menu-border-color", value);
        } else {
            // A header with a bottom (or right) border only uses the first width.
            const cssValues =
                styleName === "border-width"
                    ? { "menu-border-bottom-width": value.split(" ")[0] }
                    : {};
            customizeWebsite.previewWebsiteVariables(
                { [`menu-${styleName}`]: value },
                "null",
                cssValues
            );
        }
    }
}

export class SetShadowModeHeaderAction extends SetShadowModeAction {
    static id = "setShadowModeHeader";
    static dependencies = ["customizeWebsite"];
    apply({ value: shadowMode }) {
        this.dependencies.customizeWebsite.previewWebsiteVariables({
            "menu-box-shadow-style": getDefaultShadow(shadowMode),
        });
    }
}

export class SetShadowStyleHeaderAction extends SetShadowStyleAction {
    static id = "setShadowStyleHeader";
    static dependencies = ["customizeWebsite"];
    apply({ editingElement, params: { mainParam: attributeName }, value }) {
        const shadow = getCurrentShadow(editingElement);
        shadow[attributeName] = value;
        this.dependencies.customizeWebsite.previewWebsiteVariables({
            "menu-box-shadow-style": shadowToString(shadow),
        });
    }
}

export class SetShadowClassHeaderAction extends BuilderAction {
    static id = "setShadowClassHeader";
    static dependencies = ["customizeWebsite"];
    isApplied({ params: { mainParam: shadowClass } }) {
        const currentShadowClass =
            this.dependencies.customizeWebsite.getWebsiteVariableValue("menu-shadow-class");
        return currentShadowClass === shadowClass;
    }
    apply({ params: { mainParam: shadowClass } }) {
        const customizeWebsite = this.dependencies.customizeWebsite;
        // `none` for the preview rules (see `theme_preview.scss`).
        customizeWebsite.previewWebsiteVariables({ "menu-shadow-class": shadowClass }, "''", {
            "menu-shadow-class": shadowClass || "none",
        });
        if (shadowClass === "o-shadow-custom") {
            customizeWebsite.previewWebsiteVariables({
                "menu-box-shadow-style": getDefaultShadow(),
            });
        }
    }
    clean() {
        const customizeWebsite = this.dependencies.customizeWebsite;
        if (customizeWebsite.getWebsiteVariableValue("menu-shadow-class") === "o-shadow-custom") {
            customizeWebsite.previewWebsiteVariables({ "menu-box-shadow-style": "" });
        }
    }
}

registry.category("website-plugins").add(HeaderBoxOptionPlugin.id, HeaderBoxOptionPlugin);
