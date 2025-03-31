import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { rgbToHex } from "@web/core/utils/colors";

class WebsitePageConfigOptionPlugin extends Plugin {
    static id = "websitePageConfigOptionPlugin";
    static dependencies = ["history"];
    resources = {
        builder_actions: this.getActions(),
        builder_options: [
            {
                template: "html_builder.TopMenuVisibilityOption",
                selector:
                    "[data-main-object]:has(input.o_page_option_data[name='header_visible']) #wrapwrap > header",
                editableOnly: false,
            },
            {
                template: "html_builder.HideFooterOption",
                selector:
                    "[data-main-object]:has(input.o_page_option_data[name='footer_visible']) #wrapwrap > footer",
                editableOnly: false,
            },
        ],
        save_handlers: this.onSave.bind(this),
    };

    getActions() {
        return {
            setWebsiteHeaderVisibility: {
                apply: ({ editingElement, value: headerPositionValue }) => {
                    const lastValue = this.getVisibilityItem();
                    this.dependencies.history.applyCustomMutation({
                        apply: () => this.visibilityHandlers[headerPositionValue](),
                        revert: () => this.visibilityHandlers[lastValue](),
                    });

                    this.isDirty = true;
                },
                isApplied: ({ editingElement, value }) => this.getVisibilityItem() === value,
            },
            setPageWebsiteDirty: {
                apply: ({ editingElement }) => {
                    this.isDirty = true;
                },
            },
        };
    }

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
        return matchingClass || rgbToHex(headerEl.style.getPropertyValue(attribute));
    }

    onSave() {
        if (!this.isDirty) {
            return;
        }
        const item = this.getVisibilityItem();
        const mainObject = this.services.website.currentWebsite.metadata.mainObject;
        return Promise.all([
            this.services.orm.write(mainObject.model, [mainObject.id], {
                header_overlay: item === "overTheContent",
                header_visible: item !== "hidden",
                header_color: this.getColorValue("background-color", "bg-o-color-"),
                header_text_color: this.getColorValue("color", "text-o-color-"),
                footer_visible: !this.getFooterVisibility(),
            }),
        ]);
    }

    visibilityHandlers = {
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

    setHeaderOverlay(shouldApply) {
        this.document.getElementById("wrapwrap").classList.toggle("o_header_overlay", shouldApply);
    }

    setHeaderVisible(shouldApply) {
        const headerEl = this.document.querySelector("#wrapwrap > header");
        headerEl.classList.toggle("d-none", shouldApply);
        headerEl.classList.toggle("o_snippet_invisible", shouldApply);
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

registry
    .category("website-plugins")
    .add(WebsitePageConfigOptionPlugin.id, WebsitePageConfigOptionPlugin);
