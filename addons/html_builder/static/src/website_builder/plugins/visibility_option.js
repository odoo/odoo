import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { pyToJsLocale } from "@web/core/l10n/utils";
import { Component } from "@odoo/owl";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { useIsActiveItem } from "@html_builder/core/building_blocks/utils";

export const device_visibility_option_selector = "section .row > div";

class VisibilityOptionPlugin extends Plugin {
    static id = "VisibilityOption";
    static dependencies = ["builder-options", "visibility", "websiteSession"];
    websiteService = this.services.website;
    visibilityOptionSelector = "section, .s_hr";
    deviceSelector = "section .row > div";
    resources = {
        builder_options: [
            {
                OptionComponent: VisibilityOption,
                props: {
                    websiteSession: this.dependencies.websiteSession.getSession(),
                },
                selector: this.visibilityOptionSelector,
                cleanForSave: this.dependencies.visibility.cleanForSaveVisibility,
            },
            {
                template: "html_builder.DeviceVisibilityOption",
                selector: this.deviceSelector,
                exclude: ".s_col_no_resize.row > div, .s_masonry_block .s_col_no_resize",
                cleanForSave: this.dependencies.visibility.cleanForSaveVisibility,
            },
        ],
        builder_actions: this.getActions(),
        target_show: this.onTargetShow.bind(this),
        target_hide: this.onTargetHide.bind(this),
        normalize_handlers: this.normalizeCSSSelectors.bind(this),
        visibility_selector_parameters: [
            {
                saveAttribute: "visibilityValueCountry",
                attributeName: "data-country",
                callWith: "code",
            },
            {
                saveAttribute: "visibilityValueLang",
                attributeName: "lang",
                callWith: "code",
            },
            {
                saveAttribute: "visibilityValueUtmCampaign",
                attributeName: "data-utm-campaign",
                callWith: "name", // "display_name",
            },
            {
                saveAttribute: "visibilityValueUtmMedium",
                attributeName: "data-utm-medium",
                callWith: "name", // "display_name",
            },
            {
                saveAttribute: "visibilityValueUtmSource",
                attributeName: "data-utm-source",
                callWith: "name", // "display_name",
            },
            {
                saveAttribute: "visibilityValueLogged",
                attributeName: "data-logged",
                callWith: "value",
            },
        ],
    };
    setup() {
        this.optionsAttributes = this.getResource("visibility_selector_parameters");
    }
    getActions() {
        return {
            forceVisible: {
                apply: ({ editingElement: el }) => {
                    this.dispatchTo("on_option_visibility_update", {
                        editingEl: el,
                        show: true,
                    });
                    this.dependencies["builder-options"].updateContainers(el);
                },
                isApplied: () => true,
            },
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
        this.dependencies.visibility.hideInvisibleEl(editingEl);
    }
    onTargetShow(editingEl) {
        this.dependencies.visibility.showInvisibleEl(editingEl);
    }
    normalizeCSSSelectors(rootEl) {
        for (const el of selectElements(rootEl, this.visibilityOptionSelector)) {
            this.updateCSSSelectors(el);
        }
    }
    /**
     * Reads target's attributes and creates CSS selectors.
     * Stores them in data-attributes to then be reapplied by
     * content/inject_dom.js (ideally we should save them in a <style> tag
     * directly but that would require a new website.page field and would not
     * be possible in dynamic (controller) pages... maybe some day).
     *
     * @param {HTMLElement} target
     */
    updateCSSSelectors(target) {
        if (target.dataset.visibility !== "conditional") {
            // Cleanup on always visible
            delete target.dataset.visibility;
            for (const attribute of this.optionsAttributes) {
                delete target.dataset[attribute.saveAttribute];
                delete target.dataset[`${attribute.saveAttribute}Rule`];
            }
            delete target.dataset.visibilitySelectors;
            delete target.dataset.visibilityId;
            return;
        }
        // There are 2 data attributes per option:
        // - One that stores the current records selected
        // - Another that stores the value of the rule "Hide for / Visible for"
        const visibilityIDParts = [];
        const onlyAttributes = [];
        const hideAttributes = [];
        for (const attribute of this.optionsAttributes) {
            if (target.dataset[attribute.saveAttribute]) {
                let records = JSON.parse(target.dataset[attribute.saveAttribute]).map((record) => ({
                    id: record.id,
                    value: record[attribute.callWith],
                }));
                if (attribute.saveAttribute === "visibilityValueLang") {
                    records = records.map((lang) => {
                        lang.value = pyToJsLocale(lang.value);
                        return lang;
                    });
                }
                const hideFor = target.dataset[`${attribute.saveAttribute}Rule`] === "hide";
                if (hideFor) {
                    hideAttributes.push({ name: attribute.attributeName, records: records });
                } else {
                    onlyAttributes.push({ name: attribute.attributeName, records: records });
                }
                // Create a visibilityId based on the options name and their
                // values. eg : hide for en_US(id:1) -> lang1h
                const type = attribute.attributeName.replace("data-", "");
                const valueIDs = records.map((record) => record.id).sort();
                visibilityIDParts.push(`${type}_${hideFor ? "h" : "o"}_${valueIDs.join("_")}`);
            }
        }
        const visibilityId = visibilityIDParts.join("_");
        // Creates CSS selectors based on those attributes, the reducers
        // combine the attributes' values.
        let selectors = "";
        for (const attribute of onlyAttributes) {
            // e.g of selector:
            // html:not([data-attr-1="valueAttr1"]):not([data-attr-1="valueAttr2"]) [data-visibility-id="ruleId"]
            const selector =
                attribute.records.reduce(
                    (acc, record) => (acc += `:not([${attribute.name}="${record.value}"])`),
                    "html"
                ) + ` body:not(.editor_enable) [data-visibility-id="${visibilityId}"]`;
            selectors += selector + ", ";
        }
        for (const attribute of hideAttributes) {
            // html[data-attr-1="valueAttr1"] [data-visibility-id="ruleId"],
            // html[data-attr-1="valueAttr2"] [data-visibility-id="ruleId"]
            const selector = attribute.records.reduce((acc, record, i, a) => {
                acc += `html[${attribute.name}="${record.value}"] body:not(.editor_enable) [data-visibility-id="${visibilityId}"]`;
                return acc + (i !== a.length - 1 ? "," : "");
            }, "");
            selectors += selector + ", ";
        }
        selectors = selectors.slice(0, -2);
        if (selectors) {
            target.dataset.visibilitySelectors = selectors;
        } else {
            delete target.dataset.visibilitySelectors;
        }

        if (visibilityId) {
            target.dataset.visibilityId = visibilityId;
        } else {
            delete target.dataset.visibilityId;
        }
    }
}

class VisibilityOption extends Component {
    static template = "html_builder.VisibilityOption";
    static props = {
        websiteSession: true,
    };
    static components = { ...defaultBuilderComponents };

    setup() {
        this.isActiveItem = useIsActiveItem();
    }
}

registry.category("website-plugins").add(VisibilityOptionPlugin.id, VisibilityOptionPlugin);
