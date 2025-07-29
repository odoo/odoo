import { Plugin } from "@html_editor/plugin";
import { isMobileView } from "@html_builder/utils/utils";
import { withSequence } from "@html_editor/utils/resource";

export class VisibilityPlugin extends Plugin {
    static id = "visibility";
    static dependencies = ["builderOptions", "disableSnippets"];
    static shared = [
        "toggleTargetVisibility",
        "cleanForSaveVisibility",
        "onOptionVisibilityUpdate",
    ];
    resources = {
        on_mobile_preview_clicked: withSequence(10, this.onMobilePreviewClicked.bind(this)),
        system_attributes: ["data-invisible"],
        system_classes: ["o_snippet_override_invisible"],
    };

    setup() {
        // Add the `data-invisible="1"` attribute on the elements that are
        // really hidden, and remove it from the ones that are in fact visible,
        // depending on if we are in mobile preview or not, so the DOM is
        // consistent.
        const isMobilePreview = isMobileView(this.editable);
        this.editable
            .querySelectorAll(".o_snippet_mobile_invisible, .o_snippet_desktop_invisible")
            .forEach((invisibleEl) => {
                const isMobileHidden = invisibleEl.matches(".o_snippet_mobile_invisible");
                const isDesktopHidden = invisibleEl.matches(".o_snippet_desktop_invisible");
                if ((isMobileHidden && isMobilePreview) || (isDesktopHidden && !isMobilePreview)) {
                    invisibleEl.setAttribute("data-invisible", "1");
                } else {
                    invisibleEl.removeAttribute("data-invisible");
                }
            });
    }

    cleanForSaveVisibility(editingEl) {
        const show =
            !editingEl.classList.contains("o_snippet_invisible") &&
            !editingEl.classList.contains("o_snippet_mobile_invisible") &&
            !editingEl.classList.contains("o_snippet_desktop_invisible");
        this.toggleTargetVisibility(editingEl, show);
        const overrideInvisibleEls = [
            editingEl,
            ...editingEl.querySelectorAll(".o_snippet_override_invisible"),
        ];
        for (const overrideInvisibleEl of overrideInvisibleEls) {
            overrideInvisibleEl.classList.remove("o_snippet_override_invisible");
        }

        // Remove data-invisible attribute from condtionally hidden elements.
        // TODO do it for all invisible elements in general ?
        const conditionalHiddenEls = [
            ...editingEl.querySelectorAll("[data-visibility='conditional']"),
        ];
        if (editingEl.matches("[data-visibility='conditional']")) {
            conditionalHiddenEls.unshift(editingEl);
        }
        conditionalHiddenEls.forEach((el) => el.removeAttribute("data-invisible"));
    }

    onMobilePreviewClicked() {
        const invisibleOverrideEls = this.editable.querySelectorAll(
            ".o_snippet_mobile_invisible, .o_snippet_desktop_invisible"
        );
        for (const invisibleOverrideEl of [...invisibleOverrideEls]) {
            invisibleOverrideEl.classList.remove("o_snippet_override_invisible");
            const show = this.toggleVisibilityStatus({
                editingEl: invisibleOverrideEl,
                considerDeviceVisibility: true,
            });
            if (
                !show &&
                invisibleOverrideEl.contains(this.dependencies["builderOptions"].getTarget())
            ) {
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
     * @returns {Boolean}
     */
    toggleTargetVisibility(editingEl, show, considerDeviceVisibility) {
        show = this.toggleVisibilityStatus({ editingEl, show, considerDeviceVisibility });
        const dispatchName = show ? "target_show" : "target_hide";
        this.dispatchTo(dispatchName, editingEl);
        return show;
    }

    /**
     * Called when an option changed the visibility of its editing element.
     *
     * @param {HTMLElement} editingEl the editing element
     * @param {Boolean} show true/false if the element was shown/hidden
     */
    onOptionVisibilityUpdate(editingEl, show) {
        const isShown = this.toggleVisibilityStatus({ editingEl, show });
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
    toggleVisibilityStatus({ editingEl, show, considerDeviceVisibility = false }) {
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
}

function isTargetVisible(editingEl) {
    return editingEl.dataset.invisible !== "1";
}
