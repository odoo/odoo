import {
    getCurrentShadow,
    getDefaultShadow,
    SetShadowAction,
    SetShadowModeAction,
    shadowToString,
} from "@html_builder/plugins/shadow_option_plugin";
import { StyleAction } from "@html_builder/core/core_builder_action_plugin";
import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { HeaderBoxOption } from "./header_box_option";
import { HEADER_BOX } from "./header_option_plugin";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class HeaderTemplateOption extends BaseOptionComponent {
    static template = "website.headerTemplateOption";
    static selector = "#wrapwrap > header";
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

export class HeaderContentWidthOption extends BaseOptionComponent {
    static template = "website.headerContentWidthOption";
    static selector = "#wrapwrap > header";
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

export class HeaderSidebarWidthOption extends BaseOptionComponent {
    static template = "website.headerSidebarWidthOption";
    static selector = "#wrapwrap > header";
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

export class HeaderBackgroundOption extends BaseOptionComponent {
    static template = "website.headerBackgroundOption";
    static selector = "#wrapwrap > header";
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

export class HeaderScrollEffectOption extends BaseOptionComponent {
    static template = "website.headerScrollEffectOption";
    static selector = "#wrapwrap > header";
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

class HeaderBoxOptionPlugin extends Plugin {
    static id = "HeaderBoxOptionPlugin";
    static dependencies = ["customizeWebsite"];

    resources = {
        builder_options: [withSequence(HEADER_BOX, HeaderBoxOption)],
        builder_actions: {
            StyleActionHeaderAction,
            SetShadowModeHeaderAction,
            SetShadowHeaderAction,
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
        const defaultShadow = shadowMode === "none" ? "none" : getDefaultShadow(shadowMode);
        return this.dependencies.customizeWebsite.customizeWebsiteVariables({
            "menu-box-shadow": defaultShadow,
        });
    }
}

export class SetShadowHeaderAction extends SetShadowAction {
    static id = "setShadowHeader";
    static dependencies = ["customizeWebsite"];
    setup() {
        this.preview = false;
        this.dependencies.customizeWebsite.withCustomHistory(this);
    }
    async apply({ editingElement, params: { mainParam: attributeName }, value }) {
        const shadow = getCurrentShadow(editingElement);
        shadow[attributeName] = value;

        return this.dependencies.customizeWebsite.customizeWebsiteVariables({
            "menu-box-shadow": shadowToString(shadow),
        });
    }
}

registry.category("website-plugins").add(HeaderBoxOptionPlugin.id, HeaderBoxOptionPlugin);
