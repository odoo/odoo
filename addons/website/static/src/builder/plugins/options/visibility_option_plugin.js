import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { pyToJsLocale } from "@web/core/l10n/utils";
import { getElementsWithOption } from "@html_builder/utils/utils";
import { VisibilityOption } from "./visibility_option";
import { withSequence } from "@html_editor/utils/resource";
import { CONDITIONAL_VISIBILITY, DEVICE_VISIBILITY } from "@website/builder/option_sequence";

export const VISIBILITY_OPTION_SELECTOR = "section, .s_hr";
export const DEVICE_VISIBILITY_OPTION_SELECTOR = "section .row > div";

class VisibilityOptionPlugin extends Plugin {
    static id = "visibilityOption";
    static dependencies = ["visibility", "websiteSession"];
    resources = {
        builder_options: [
            withSequence(CONDITIONAL_VISIBILITY, {
                OptionComponent: VisibilityOption,
                props: {
                    websiteSession: this.dependencies.websiteSession.getSession(),
                },
                selector: VISIBILITY_OPTION_SELECTOR,
                cleanForSave: this.dependencies.visibility.cleanForSaveVisibility,
            }),
            withSequence(DEVICE_VISIBILITY, {
                template: "website.DeviceVisibilityOption",
                selector: DEVICE_VISIBILITY_OPTION_SELECTOR,
                exclude: ".s_col_no_resize.row > div, .s_masonry_block .s_col_no_resize",
                cleanForSave: this.dependencies.visibility.cleanForSaveVisibility,
            }),
        ],
        builder_actions: this.getActions(),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
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
                apply: ({ editingElement }) => {
                    this.dependencies.visibility.onOptionVisibilityUpdate(editingElement, true);
                },
                isApplied: () => true,
            },
            toggleDeviceVisibility: {
                apply: ({ editingElement, params: { mainParam: visibility } }) => {
                    // Clean first as the widget is not part of a group
                    this.clean(editingElement);
                    const style = getComputedStyle(editingElement);
                    if (visibility === "no_desktop") {
                        editingElement.classList.add("d-lg-none", "o_snippet_desktop_invisible");
                    } else if (visibility === "no_mobile") {
                        editingElement.classList.add(
                            `d-lg-${style["display"]}`,
                            "d-none",
                            "o_snippet_mobile_invisible"
                        );
                    }

                    // Update invisible elements
                    const isMobile = this.services.website.context.isMobile;
                    const show = visibility !== (isMobile ? "no_mobile" : "no_desktop");
                    this.dependencies.visibility.onOptionVisibilityUpdate(editingElement, show);
                },
                clean: ({ editingElement }) => {
                    this.clean(editingElement);
                },
                isApplied: ({ editingElement, params: { mainParam: visibility } }) =>
                    this.isApplied(editingElement, visibility),
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

    onSnippetDropped({ snippetEl }) {
        const selector = [VISIBILITY_OPTION_SELECTOR, DEVICE_VISIBILITY_OPTION_SELECTOR].join(", ");
        const droppedEls = getElementsWithOption(snippetEl, selector);
        droppedEls.forEach((droppedEl) =>
            this.dependencies.visibility.toggleTargetVisibility(droppedEl, true, true)
        );
    }

    normalizeCSSSelectors(rootEl) {
        for (const el of selectElements(rootEl, VISIBILITY_OPTION_SELECTOR)) {
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

registry.category("website-plugins").add(VisibilityOptionPlugin.id, VisibilityOptionPlugin);
