import { Plugin } from "@html_editor/plugin";
import { getElementsWithOption, isMobileView } from "@html_builder/utils/utils";
import { withSequence } from "@html_editor/utils/resource";

const invisibleElementsSelector =
    ".o_snippet_invisible, .o_snippet_mobile_invisible, .o_snippet_desktop_invisible";
const deviceInvisibleSelector = ".o_snippet_mobile_invisible, .o_snippet_desktop_invisible";

export class VisibilityPlugin extends Plugin {
    static id = "visibility";
    static dependencies = ["builderOptions", "disableSnippets"];
    static shared = ["toggleTargetVisibility", "onOptionVisibilityUpdate", "hideElement"];
    resources = {
        on_mobile_preview_clicked: withSequence(10, this.onMobilePreviewClicked.bind(this)),
        system_attributes: ["data-invisible"],
        system_classes: ["o_snippet_override_invisible"],
        clean_for_save_handlers: this.cleanForSaveVisibility.bind(this),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    setup() {
        // Add the `data-invisible="1"` attribute on the elements that are
        // really hidden, and remove it from the ones that are in fact visible,
        // depending on if we are in mobile preview or not, so the DOM is
        // consistent.
        const isMobilePreview = isMobileView(this.editable);
        this.editable.querySelectorAll(deviceInvisibleSelector).forEach((invisibleEl) => {
            const isMobileHidden = invisibleEl.matches(".o_snippet_mobile_invisible");
            const isDesktopHidden = invisibleEl.matches(".o_snippet_desktop_invisible");
            if ((isMobileHidden && isMobilePreview) || (isDesktopHidden && !isMobilePreview)) {
                invisibleEl.setAttribute("data-invisible", "1");
            } else {
                invisibleEl.removeAttribute("data-invisible");
            }
        });
    }

    cleanForSaveVisibility({ root: rootEl }) {
        const invisibleEls = getElementsWithOption(rootEl, invisibleElementsSelector);
        for (const invisibleEl of invisibleEls) {
            // Hide the invisible elements.
            this.toggleTargetVisibility(invisibleEl, false, false, true);
            // Remove the `data-invisible` attribute from conditionally hidden
            // elements.
            if (invisibleEl.matches("[data-visibility='conditional']")) {
                invisibleEl.removeAttribute("data-invisible");
            }
        }
    }

    onSnippetDropped({ snippetEl }) {
        // Show the invisible elements.
        const invisibleEls = getElementsWithOption(snippetEl, invisibleElementsSelector);
        for (const invisibleEl of invisibleEls) {
            this.toggleTargetVisibility(invisibleEl, true);
        }
    }

    onMobilePreviewClicked() {
        const deviceInvisibleEls = this.editable.querySelectorAll(deviceInvisibleSelector);
        const currentContainerTargetEl = this.dependencies["builderOptions"].getTarget();
        for (const deviceInvisibleEl of [...deviceInvisibleEls]) {
            deviceInvisibleEl.classList.remove("o_snippet_override_invisible");
            const show = !isTargetVisible(deviceInvisibleEl);
            const isShown = this.toggleVisibilityStatus(deviceInvisibleEl, show, true);
            if (!isShown && deviceInvisibleEl.contains(currentContainerTargetEl)) {
                this.dependencies["builderOptions"].deactivateContainers();
            }
        }
    }

    /**
     * Toggles the visibility of the given element.
     *
     * @param {HTMLElement} editingEl
     * @param {Boolean} show true to show the element, false to hide it
     * @param {Boolean} considerDeviceVisibility
     * @param {Boolean} [isCleaning=false] true if the function is called by the
     * clean_for_save handler.
     * @returns {Boolean}
     */
    toggleTargetVisibility(editingEl, show, considerDeviceVisibility, isCleaning = false) {
        show = this.toggleVisibilityStatus(editingEl, show, considerDeviceVisibility);
        const resourceName = show ? "target_show" : "target_hide";
        this.dispatchTo(resourceName, editingEl);
        return show;
    }

    /**
     * Called when an option changed the visibility of its editing element.
     *
     * @param {HTMLElement} editingEl the editing element
     * @param {Boolean} show true/false if the element was shown/hidden
     */
    onOptionVisibilityUpdate(editingEl, show) {
        const isShown = this.toggleVisibilityStatus(editingEl, show);
        if (!isShown) {
            this.dependencies.builderOptions.setNextTarget(false);
        }
        this.config.updateInvisibleElementsPanel();
        this.dependencies.disableSnippets.disableUndroppableSnippets();
    }

    /**
     * Sets/removes the `data-invisible` attribute on the given element,
     * depending on if it is considered as hidden/shown.
     *
     * @param {HTMLElement} editingEl the element
     * @param {Boolean} show
     * @param {Boolean} considerDeviceVisibility
     * @returns {Boolean}
     */
    toggleVisibilityStatus(editingEl, show, considerDeviceVisibility = false) {
        if (
            considerDeviceVisibility &&
            editingEl.matches(".o_snippet_mobile_invisible, .o_snippet_desktop_invisible")
        ) {
            const isMobilePreview = isMobileView(editingEl);
            const isMobileHidden = editingEl.classList.contains("o_snippet_mobile_invisible");
            show = isMobilePreview !== isMobileHidden;
        }

        if (show === undefined) {
            show = !isTargetVisible(editingEl);
        }
        if (show) {
            delete editingEl.dataset.invisible;
        } else {
            editingEl.dataset.invisible = "1";
        }
        return show;
    }

    /**
     * Hides the given element and updates what needs to be.
     * Note: to use only when hiding things without adding history steps:
     * - if an action adding a history step hides the element, it should call
     *   `onOptionVisibilityUpdate`
     * - if it concerns the "Invisible Element" panel, refer to its component.
     *
     * @param {HTMLElement} toHideEl the element to hide.
     */
    hideElement(toHideEl) {
        this.toggleTargetVisibility(toHideEl, false);
        this.dependencies.builderOptions.deactivateContainers();
        this.config.updateInvisibleElementsPanel();
        this.dependencies.disableSnippets.disableUndroppableSnippets();
    }
}

function isTargetVisible(editingEl) {
    return editingEl.dataset.invisible !== "1";
}
