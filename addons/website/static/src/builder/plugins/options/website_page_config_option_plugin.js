import { after } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { rgbaToHex } from "@web/core/utils/colors";
import { withSequence } from "@html_editor/utils/resource";
import { FOOTER_COPYRIGHT } from "./footer_option_plugin";
import { HEADER_TEMPLATE } from "./header/header_option_plugin";
import { TopMenuVisibilityOption } from "./website_page_config_option";
import { BuilderAction } from "@html_builder/core/builder_action";

export const TOP_MENU_VISIBILITY = after(HEADER_TEMPLATE);
export const HIDE_FOOTER = after(FOOTER_COPYRIGHT);

class WebsitePageConfigOptionPlugin extends Plugin {
    static id = "websitePageConfigOptionPlugin";
    static dependencies = ["history", "visibility"];
    static shared = ["setDirty", "setFooterVisible", "getVisibilityItem", "getFooterVisibility"];
    resources = {
        builder_actions: {
            SetWebsiteHeaderVisibilityAction,
            SetWebsiteFooterVisibleAction,
            SetPageWebsiteDirtyAction,
        },
        builder_options: [
            withSequence(TOP_MENU_VISIBILITY, {
                OptionComponent: TopMenuVisibilityOption,
                selector:
                    "[data-main-object]:has(input.o_page_option_data[name='header_visible']) #wrapwrap > header",
                editableOnly: false,
                groups: ["website.group_website_designer"],
                props: {
                    doesPageOptionExist: this.doesPageOptionExist.bind(this),
                },
            }),
            withSequence(HIDE_FOOTER, {
                template: "website.HideFooterOption",
                selector:
                    "[data-main-object]:has(input.o_page_option_data[name='footer_visible']) #wrapwrap > footer",
                editableOnly: false,
                groups: ["website.group_website_designer"],
            }),
        ],
        target_show: this.onTargetVisibilityToggle.bind(this, true),
        target_hide: this.onTargetVisibilityToggle.bind(this, false),
        save_handlers: this.onSave.bind(this),
    };

    getVisibilityItem() {
        const isHidden = this.document
            .querySelector("#wrapwrap > header")
            .classList.contains("o_snippet_invisible");
        const isOverlay = this.document
            .getElementById("wrapwrap")
            .classList.contains("o_header_overlay");
        return isOverlay ? "overTheContent" : isHidden ? "hidden" : "regular";
    }

    getFooterVisibility() {
        return this.document
            .querySelector("#wrapwrap > footer")
            .classList.contains("o_snippet_invisible");
    }

    getColorValue(attribute, classPrefix) {
        const headerEl = this.document.querySelector("#wrapwrap > header");
        const matchingClass = [...headerEl.classList].find((cls) => cls.startsWith(classPrefix));
        return matchingClass || rgbaToHex(headerEl.style.getPropertyValue(attribute));
    }

    setDirty() {
        this.isDirty = true;
    }

    onSave() {
        if (!this.isDirty) {
            return;
        }
        const item = this.getVisibilityItem();
        const pageOptions = {
            header_overlay: () => item === "overTheContent",
            header_color: () => this.getColorValue("background-color", "bg-"),
            header_text_color: () => this.getColorValue("color", "text-"),
            header_visible: () => item !== "hidden",
            footer_visible: () => !this.getFooterVisibility(),
        };

        const args = {};
        for (const [pageOptionName, valueGetter] of Object.entries(pageOptions)) {
            if (this.doesPageOptionExist(pageOptionName)) {
                args[pageOptionName] = valueGetter();
            }
        }

        const mainObject = this.services.website.currentWebsite.metadata.mainObject;
        return Promise.all([this.services.orm.write(mainObject.model, [mainObject.id], args)]);
    }

    doesPageOptionExist(pageOptionName) {
        return this.document.querySelector(
            `[data-main-object]:has(input.o_page_option_data[name='${pageOptionName}'])`
        );
    }

    setFooterVisible(show) {
        const footerEl = this.document.querySelector("#wrapwrap > footer");
        footerEl.classList.toggle("d-none", !show);
        footerEl.classList.toggle("o_snippet_invisible", !show);
        this.dependencies.visibility.onOptionVisibilityUpdate(footerEl, show);
    }

    onTargetVisibilityToggle(show, target) {
        if (target.matches("#wrapwrap > header, #wrapwrap > footer")) {
            this.dependencies.history.ignoreDOMMutations(() => {
                target.classList.toggle("d-none", !show);
            });
        }
    }
}
export class BaseWebsitePageConfigAction extends BuilderAction {
    static id = "baseWebsitePageConfig";
    static dependencies = ["websitePageConfigOptionPlugin", "history", "visibility"];
    setup() {
        this.websitePageConfig = this.dependencies.websitePageConfigOptionPlugin;
        this.visibility = this.dependencies.visibility;
        this.history = this.dependencies.history;
        this.visibilityHandlers = {
            overTheContent: () => {
                this.setHeaderOverlay(true);
                this.setHeaderVisible(false);
            },
            regular: () => {
                this.setHeaderOverlay(false);
                this.setHeaderVisible(false);
                this.resetHeaderColor();
                this.resetTextColor();
            },
            hidden: () => {
                this.setHeaderOverlay(false);
                this.setHeaderVisible(true);
                this.resetHeaderColor();
                this.resetTextColor();
            },
        };
    }

    setHeaderOverlay(shouldApply) {
        this.document.getElementById("wrapwrap").classList.toggle("o_header_overlay", shouldApply);
    }

    setHeaderVisible(shouldApply) {
        const headerEl = this.document.querySelector("#wrapwrap > header");
        headerEl.classList.toggle("d-none", shouldApply);
        headerEl.classList.toggle("o_snippet_invisible", shouldApply);
        this.visibility.onOptionVisibilityUpdate(headerEl, !shouldApply);
    }

    resetHeaderColor() {
        const headerEl = this.document.querySelector("#wrapwrap > header");
        headerEl.style.removeProperty("background-color");
        headerEl.classList.forEach((cls) => {
            if (cls.startsWith("bg-o-color-")) {
                headerEl.classList.remove(cls);
            }
        });
    }

    resetTextColor() {
        const headerEl = this.document.querySelector("#wrapwrap > header");
        headerEl.style.removeProperty("color");
        headerEl.classList.forEach((cls) => {
            if (cls.startsWith("text-o-color-")) {
                headerEl.classList.remove(cls);
            }
        });
    }
}
export class SetWebsiteHeaderVisibilityAction extends BaseWebsitePageConfigAction {
    static id = "setWebsiteHeaderVisibility";
    apply({ editingElement, value: headerPositionValue }) {
        const lastValue = this.websitePageConfig.getVisibilityItem();
        this.history.applyCustomMutation({
            apply: () => this.visibilityHandlers[headerPositionValue](),
            revert: () => this.visibilityHandlers[lastValue](),
        });

        this.websitePageConfig.setDirty();
    }
    isApplied({ editingElement, value }) {
        return this.websitePageConfig.getVisibilityItem() === value;
    }
}
export class SetWebsiteFooterVisibleAction extends BaseWebsitePageConfigAction {
    static id = "setWebsiteFooterVisible";
    isApplied({ editingElement }) {
        return !this.websitePageConfig.getFooterVisibility();
    }
    apply({ editingElement }) {
        this.websitePageConfig.setFooterVisible(true);
        this.websitePageConfig.setDirty();
    }
    clean({ editingElement }) {
        this.websitePageConfig.setFooterVisible(false);
        this.websitePageConfig.setDirty();
    }
}

export class SetPageWebsiteDirtyAction extends BaseWebsitePageConfigAction {
    static id = "setPageWebsiteDirty";
    apply({ editingElement }) {
        this.websitePageConfig.setDirty();
    }
}

registry
    .category("website-plugins")
    .add(WebsitePageConfigOptionPlugin.id, WebsitePageConfigOptionPlugin);
