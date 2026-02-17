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
    setup() {
        this.preview = false;
        this.dependencies.customizeWebsite.withCustomHistory(this);
    }
    getValue(...args) {
        const { params } = args[0];
        const value = super.getValue(...args);
        if (params.mainParam === "border-width") {
            return value.replace(/(^|\s)0px/gi, "").trim() || value;
        }
        return value;
    }
    async apply({ params, value }) {
        const styleName = params.mainParam;

        if (styleName === "border-color") {
            return this.dependencies.customizeWebsite.customizeWebsiteColors({
                "menu-border-color": value,
            });
        }
        return this.dependencies.customizeWebsite.customizeWebsiteVariables({
            [`menu-${styleName}`]: value,
        });
    }
}

export class SetShadowModeHeaderAction extends SetShadowModeAction {
    static id = "setShadowModeHeader";
    static dependencies = ["customizeWebsite"];
    setup() {
        this.preview = false;
        this.dependencies.customizeWebsite.withCustomHistory(this);
    }
    async apply({ value: shadowMode }) {
        const defaultShadow = getDefaultShadow(shadowMode);
        return this.dependencies.customizeWebsite.customizeWebsiteVariables({
            "menu-box-shadow-style": defaultShadow,
        });
    }
}

export class SetShadowStyleHeaderAction extends SetShadowStyleAction {
    static id = "setShadowStyleHeader";
    static dependencies = ["customizeWebsite"];
    setup() {
        this.preview = false;
        this.dependencies.customizeWebsite.withCustomHistory(this);
    }
    async apply({ editingElement, params: { mainParam: attributeName }, value }) {
        const shadow = getCurrentShadow(editingElement);
        shadow[attributeName] = value;

        return this.dependencies.customizeWebsite.customizeWebsiteVariables({
            "menu-box-shadow-style": shadowToString(shadow),
        });
    }
}

export class SetShadowClassHeaderAction extends BuilderAction {
    static id = "setShadowClassHeader";
    static dependencies = ["customizeWebsite"];
    setup() {
        this.preview = false;
        this.dependencies.customizeWebsite.withCustomHistory(this);
    }
    isApplied({ params: { mainParam: shadowClass } }) {
        const currentShadowClass =
            this.dependencies.customizeWebsite.getWebsiteVariableValue("menu-shadow-class");
        return currentShadowClass === shadowClass;
    }
    async apply({ params: { mainParam: shadowClass } }) {
        await this.dependencies.customizeWebsite.customizeWebsiteVariables(
            {
                "menu-shadow-class": shadowClass,
            },
            "''"
        );
        const currentShadowClass =
            this.dependencies.customizeWebsite.getWebsiteVariableValue("menu-shadow-class");
        if (currentShadowClass === "o-shadow-custom") {
            const defaultShadow = getDefaultShadow();
            await this.dependencies.customizeWebsite.customizeWebsiteVariables({
                "menu-box-shadow-style": defaultShadow,
            });
        }
    }
    async clean() {
        const currentShadowClass =
            this.dependencies.customizeWebsite.getWebsiteVariableValue("menu-shadow-class");
        if (currentShadowClass === "o-shadow-custom") {
            await this.dependencies.customizeWebsite.customizeWebsiteVariables({
                "menu-box-shadow-style": null,
            });
        }
    }
}

registry.category("website-plugins").add(HeaderBoxOptionPlugin.id, HeaderBoxOptionPlugin);
