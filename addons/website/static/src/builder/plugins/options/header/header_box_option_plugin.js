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

// The header's shadow per shadow class (`--o-menu-box-shadow` in the SCSS).
export const MENU_BOX_SHADOWS = {
    shadow: "var(--box-shadow)",
    "shadow-sm": "var(--box-shadow-sm)",
    "shadow-lg": "var(--box-shadow-lg)",
    "o-shadow-custom": "var(--menu-box-shadow-style)",
};

export class HeaderBoxOptionPlugin extends Plugin {
    static id = "HeaderBoxOptionPlugin";
    static dependencies = ["customizeWebsite"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            StyleActionHeaderAction,
            StyleActionHeaderColorAction,
            SetShadowClassHeaderAction,
            SetShadowModeHeaderAction,
            SetShadowStyleHeaderAction,
        },
    };
}

export class StyleActionHeaderAction extends StyleAction {
    static id = "styleActionHeader";
    static dependencies = ["customizeWebsite", "color"];
    setup() {}
    getValue(...args) {
        const { params } = args[0];
        const value = super.getValue(...args);
        if (params.mainParam === "border-width") {
            return value.replace(/(^|\s)0px/gi, "").trim() || value;
        }
        return value;
    }
    apply({ params: { mainParam: styleName }, value }) {
        const previewValues = {};
        if (styleName === "border-width") {
            // The bottom (or right) border only takes the first width.
            previewValues["o-menu-border-bottom-width"] = value.split(" ")[0];
        }
        this.dependencies.customizeWebsite.previewWebsiteVariables(
            { [`menu-${styleName}`]: value },
            "null",
            previewValues
        );
    }
}

export class StyleActionHeaderColorAction extends StyleAction {
    static id = "styleActionHeaderColor";
    static dependencies = ["customizeWebsite", "color"];
    setup() {}
    apply({ value }) {
        this.dependencies.customizeWebsite.previewWebsiteColors({ "menu-border-color": value });
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
        const variables = { "menu-shadow-class": shadowClass };
        if (shadowClass === "o-shadow-custom") {
            variables["menu-box-shadow-style"] = getDefaultShadow();
        }
        this.dependencies.customizeWebsite.previewWebsiteVariables(variables, "''", {
            // No class: shown as the empty value it's saved as.
            "menu-shadow-class": shadowClass || "''",
            "o-menu-box-shadow": MENU_BOX_SHADOWS[shadowClass] || "",
        });
    }
    clean() {
        const currentShadowClass =
            this.dependencies.customizeWebsite.getWebsiteVariableValue("menu-shadow-class");
        if (currentShadowClass === "o-shadow-custom") {
            this.dependencies.customizeWebsite.previewWebsiteVariables({
                "menu-box-shadow-style": "",
            });
        }
    }
}

registry.category("website-plugins").add(HeaderBoxOptionPlugin.id, HeaderBoxOptionPlugin);
