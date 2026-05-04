import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

/** @typedef {import("plugins").CSSSelector} CSSSelector */
/** @typedef {import("plugins").LazyTranslatedString} LazyTranslatedString */
/**
 * @typedef {{
 *      value: string;
 *      label: LazyTranslatedString;
 *      pageSelector: CSSSelector | null;
 * }[]} popup_show_on_options
 *
 * Register popup visibility scopes for the "Show on" dropdown.
 * `value` is stored in `data-show-on` on the popup.
 * `pageSelector` is stored in `data-show-on-selector` and used at runtime to
 * decide whether a shared popup should be displayed on the current page.
 */
/** @typedef {CSSSelector[]} popup_container_selectors */
/**
 * @typedef {{
 *      selector: CSSSelector;
 *      value: string;
 * }[]} popup_show_on_dropzones
 *
 * Register special dropzones that should force a popup to become a shared,
 * module-scoped popup when dropped there.
 */

const SHARED_POPUPS_CONTAINER_SELECTOR = "#o_shared_blocks";
const SHOW_ON_CURRENT_PAGE_VALUE = "currentPage";
const SHOW_ON_ALL_PAGES_VALUE = "allPages";

export class PopupOption extends BaseOptionComponent {
    static id = "popup_option";
    static template = "website.PopupOption";

    setup() {
        super.setup();
        this.showOnOptions = this.getResource("popup_show_on_options");
        this.unavailableShowOnWarningMessage = _t(
            "The selected visibility target is unavailable (module uninstalled). Choose one of the available values."
        );
        this.domState = useDomState((editingElement) => {
            const showOn = editingElement.closest(".s_popup")?.dataset.showOn || "";
            return {
                showOn,
                isUnavailableShowOn:
                    !!showOn && !this.showOnOptions.some((option) => option.value === showOn),
            };
        });
    }

    isShowOnOptionUnavailable() {
        return !!this.domState.isUnavailableShowOn;
    }
}

function getPopupContainerFromSelectors(editable, selectors) {
    for (const selector of selectors) {
        const containerEl = editable.querySelector(selector);
        if (containerEl) {
            return containerEl;
        }
    }
    return null;
}

function getPopupShowOnOption(getResource, value) {
    return getResource("popup_show_on_options").find((option) => option.value === value);
}

function syncPopupShowOnSelector(getResource, popupEl) {
    delete popupEl.dataset.showOnSelector;
    const showOnOption = getPopupShowOnOption(getResource, popupEl.dataset.showOn);
    if (!showOnOption) {
        return;
    }
    if (showOnOption.pageSelector) {
        popupEl.dataset.showOnSelector = showOnOption.pageSelector;
    }
}
export class PopupOptionPlugin extends Plugin {
    static id = "PopupOption";
    static dependencies = ["anchor", "visibility", "history", "popupVisibilityPlugin"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dropzone_selectors: {
            selector: ".s_popup",
            exclude: "#website_cookies_bar",
            excludeAncestor:
                ".s_popup, .s_table_of_content, .s_tabs, .s_tabs_images, .position-sticky",
            dropIn: ":not(p).oe_structure:not(.oe_structure_solo):not([data-snippet] *), :not(.o_mega_menu):not(p)[data-oe-type=html]:not([data-snippet] *)",
        },
        builder_actions: {
            // Moves the snippet in #o_shared_blocks to be common to all pages
            // or inside the first editable oe_structure in the main to be on
            // current page only.
            MoveBlockAction,
            SetBackdropAction,
            CopyAnchorAction,
            SetPopupDelayAction,
        },
        is_node_empty_predicates: (el) => {
            if (!el.matches?.(".s_popup")) {
                return;
            }
            const popupModalChildrenEls = [...(el.querySelector(".modal-content")?.children ?? [])];
            return popupModalChildrenEls.every((child) => child.matches(".s_popup_close"));
        },
        on_cloned_handlers: this.onCloned.bind(this),
        on_snippet_dropped_handlers: withSequence(0, this.onSnippetDropped.bind(this)),
        on_element_dropped_handlers: withSequence(0, this.onElementDropped.bind(this)),
        on_will_remove_handlers: this.onWillRemove.bind(this),
        no_parent_containers: ".s_popup",
        popup_container_selectors: withSequence(10, "main .oe_structure.o_savable"),
        popup_show_on_options: [
            withSequence(10, {
                value: SHOW_ON_CURRENT_PAGE_VALUE,
                label: _t("This page"),
                pageSelector: null,
            }),
            withSequence(20, {
                value: SHOW_ON_ALL_PAGES_VALUE,
                label: _t("All pages"),
                pageSelector: null,
            }),
        ],
    };

    onCloned({ cloneEl }) {
        if (cloneEl.matches(".s_popup")) {
            this.assignUniqueID(cloneEl);
        }
    }

    onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_popup")) {
            this.relocatePopup(snippetEl);
            snippetEl.dataset.showOn ||= SHOW_ON_CURRENT_PAGE_VALUE;
            syncPopupShowOnSelector(this.getResource.bind(this), snippetEl);
            this.assignUniqueID(snippetEl);
            this.dependencies.history.addCustomMutation({
                apply: () => {
                    this.dependencies.visibility.toggleTargetVisibility(snippetEl, true);
                },
                revert: () => {
                    this.dependencies.visibility.toggleTargetVisibility(snippetEl, false);
                },
            });
        }
    }

    onWillRemove(el) {
        this.dependencies.visibility.toggleTargetVisibility(el, false);
        this.dependencies.history.addCustomMutation({
            apply: () => {
                this.dependencies.visibility.toggleTargetVisibility(el, false);
            },
            revert: () => {
                this.dependencies.visibility.toggleTargetVisibility(el, true);
            },
        });
    }

    assignUniqueID(editingElement) {
        editingElement.closest(".s_popup").id = `sPopup${Date.now()}`;
    }

    onElementDropped({ droppedEl }) {
        if (droppedEl.matches(".s_popup")) {
            this.relocatePopup(droppedEl);
        }
    }

    relocatePopup(editingElement) {
        const popupEl = editingElement.closest(".s_popup");
        const specialDropzone = this.getResource("popup_show_on_dropzones").find(({ selector }) =>
            popupEl.closest(selector)
        );
        if (specialDropzone) {
            popupEl.dataset.showOn = specialDropzone.value;
        }

        const showOnValue = popupEl.dataset.showOn || SHOW_ON_CURRENT_PAGE_VALUE;
        const containerEl =
            showOnValue === SHOW_ON_CURRENT_PAGE_VALUE
                ? getPopupContainerFromSelectors(
                      this.editable,
                      this.getResource("popup_container_selectors")
                  )
                : this.editable.querySelector(SHARED_POPUPS_CONTAINER_SELECTOR);
        if (containerEl && popupEl.parentElement !== containerEl) {
            containerEl.insertAdjacentElement("beforeend", popupEl);
        }
        if (!popupEl.dataset.showOn) {
            popupEl.dataset.showOn = SHOW_ON_CURRENT_PAGE_VALUE;
        }
        syncPopupShowOnSelector(this.getResource.bind(this), popupEl);
    }
}

// Moves the snippet in #o_shared_blocks to be common to all pages
// or inside the first editable oe_structure in the main to be on
// current page only.
export class MoveBlockAction extends BuilderAction {
    static id = "moveBlock";
    isApplied({ editingElement, value }) {
        const popupEl = editingElement.closest(".s_popup");
        if (popupEl.dataset.showOn) {
            return popupEl.dataset.showOn === value;
        }
        return popupEl.closest(SHARED_POPUPS_CONTAINER_SELECTOR)
            ? value === SHOW_ON_ALL_PAGES_VALUE
            : value === SHOW_ON_CURRENT_PAGE_VALUE;
    }
    apply({ editingElement, value }) {
        const popupEl = editingElement.closest(".s_popup");
        popupEl.dataset.showOn = value;
        syncPopupShowOnSelector(this.getResource.bind(this), popupEl);
        const whereEl =
            value === SHOW_ON_CURRENT_PAGE_VALUE
                ? getPopupContainerFromSelectors(
                      this.editable,
                      this.getResource("popup_container_selectors")
                  )
                : this.editable.querySelector(SHARED_POPUPS_CONTAINER_SELECTOR);
        whereEl?.insertAdjacentElement("beforeend", popupEl);
    }
}
export class SetBackdropAction extends BuilderAction {
    static id = "setBackdrop";
    isApplied({ editingElement }) {
        const hasBackdropColor = !!editingElement.style.getPropertyValue("background-color").trim();
        const hasNoBackdropClass = editingElement.classList.contains("s_popup_no_backdrop");
        return hasBackdropColor && !hasNoBackdropClass;
    }
    apply({ editingElement }) {
        editingElement.classList.remove("s_popup_no_backdrop");
        editingElement.style.setProperty("background-color", "var(--black-50)", "important");
    }
    clean({ editingElement }) {
        editingElement.classList.add("s_popup_no_backdrop");
        editingElement.style.removeProperty("background-color");
    }
}
export class CopyAnchorAction extends BuilderAction {
    static id = "copyAnchor";
    static dependencies = ["anchor"];
    apply({ editingElement }) {
        this.dependencies.anchor.createOrEditAnchorLink(editingElement);
    }
}
export class SetPopupDelayAction extends BuilderAction {
    static id = "setPopupDelay";
    apply({ editingElement, value }) {
        editingElement.dataset.showAfter = value * 1000;
    }
    getValue({ editingElement }) {
        return editingElement.dataset.showAfter / 1000;
    }
}

registry.category("website-options").add(PopupOption.id, PopupOption);
registry.category("website-plugins").add(PopupOptionPlugin.id, PopupOptionPlugin);
