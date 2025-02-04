import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { applyFunDependOnSelectorAndExclude } from "@html_builder/plugins/utils";

export const device_visibility_option_selector = "section .row > div";

class VisibilityOptionPlugin extends Plugin {
    static id = "VisibilityOption";
    static dependencies = ["builder-options", "visibility"];
    websiteService = this.services.website;
    selector = "section .row > div";
    resources = {
        builder_options: [
            {
                template: "html_builder.VisibilityOption",
                selector: "section, .s_hr",
                cleanForSave: this.dependencies.visibility.cleanForSaveVisibility,
            },
            {
                template: "html_builder.DeviceVisibilityOption",
                selector: this.selector,
                exclude: ".s_col_no_resize.row > div, .s_masonry_block .s_col_no_resize",
                cleanForSave: this.cleanForSave.bind(this),
            },
        ],
        builder_actions: this.getActions(),
        target_show: this.onTargetShow.bind(this),
        target_hide: this.onTargetHide.bind(this),
    };

    cleanForSave(editingEl) {
        this.dependencies.visibility.cleanForSaveVisibility(editingEl);
        editingEl.classList.remove("o_snippet_override_invisible");
    }
    getActions() {
        return {
            toggleDeviceVisibility: {
                apply: ({ editingElement, param }) => {
                    // Clean first as the widget is not part of a group
                    this.clean(editingElement);
                    const style = getComputedStyle(editingElement);
                    if (param === "no_desktop") {
                        editingElement.classList.add("d-lg-none", "o_snippet_desktop_invisible");
                    } else if (param === "no_mobile") {
                        editingElement.classList.add(
                            `d-lg-${style["display"]}`,
                            "d-none",
                            "o_snippet_mobile_invisible"
                        );
                    }

                    // Update invisible elements
                    const isMobile = this.websiteService.context.isMobile;
                    const show = param !== (isMobile ? "no_mobile" : "no_desktop");
                    this.dispatchTo("on_option_visibility_update", {
                        editingEl: editingElement,
                        show: show,
                    });
                    this.dependencies["builder-options"].updateContainers(editingElement);
                },
                clean: ({ editingElement }) => {
                    this.clean(editingElement);
                },
                isApplied: ({ editingElement, param: visibilityParam }) =>
                    this.isApplied(editingElement, visibilityParam),
            },
        };
    }
    clean(editingElement) {
        editingElement.classList.remove(
            "d-none",
            "d-md-none",
            "d-lg-none",
            "o_snippet_mobile_invisible",
            "o_snippet_desktop_invisible",
            "o_snippet_override_invisible"
        );
        const style = getComputedStyle(editingElement);
        const display = style["display"];
        editingElement.classList.remove(`d-md-${display}`, `d-lg-${display}`);
        this.dependencies["builder-options"].updateContainers(editingElement);
    }
    isApplied(editingElement, visibilityParam) {
        const classList = [...editingElement.classList];
        if (
            visibilityParam === "no_mobile" &&
            classList.includes("d-none") &&
            classList.some((className) => className.match(/^d-(md|lg)-/))
        ) {
            return true;
        }
        if (
            visibilityParam === "no_desktop" &&
            classList.some((className) => className.match(/d-(md|lg)-none/))
        ) {
            return true;
        }
        return false;
    }
    onTargetHide(editingEl) {
        applyFunDependOnSelectorAndExclude(
            this.dependencies.visibility.hideInvisibleEl,
            editingEl,
            this.selector
        );
    }
    onTargetShow(editingEl) {
        applyFunDependOnSelectorAndExclude(
            this.dependencies.visibility.showInvisibleEl,
            editingEl,
            this.selector
        );
    }
}

registry.category("website-plugins").add(VisibilityOptionPlugin.id, VisibilityOptionPlugin);
