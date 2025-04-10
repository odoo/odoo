import { Plugin } from "@html_editor/plugin";
import { isMobileView } from "@html_builder/utils/utils";

export class VisibilityPlugin extends Plugin {
    static id = "visibility";
    static dependencies = ["builder-options", "disableSnippets"];
    static shared = [
        "toggleTargetVisibility",
        "cleanForSaveVisibility",
        "onOptionVisibilityUpdate",
    ];

    resources = {
        on_mobile_preview_clicked: this.onMobilePreviewClicked.bind(this),
        system_attributes: ["data-invisible"],
        system_classes: ["o_snippet_override_invisible"],
    };

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
    }

    onMobilePreviewClicked() {
        const isMobilePreview = isMobileView(this.editable);
        const invisibleOverrideEls = this.editable.querySelectorAll(
            ".o_snippet_mobile_invisible, .o_snippet_desktop_invisible"
        );
        for (const invisibleOverrideEl of [...invisibleOverrideEls]) {
            const isMobileHidden = invisibleOverrideEl.classList.contains(
                "o_snippet_mobile_invisible"
            );
            invisibleOverrideEl.classList.remove("o_snippet_override_invisible");
            const show = isMobilePreview !== isMobileHidden;
            this.toggleVisibilityStatus(invisibleOverrideEl, show);
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
        show = this.toggleVisibilityStatus(editingEl, show, considerDeviceVisibility);
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
        const isShown = this.toggleVisibilityStatus(editingEl, show);

        if (!isShown) {
            this.dependencies["builder-options"].deactivateContainers();
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
    toggleVisibilityStatus(editingEl, show, considerDeviceVisibility) {
        if (
            considerDeviceVisibility &&
            editingEl.matches(".o_snippet_mobile_invisible, .o_snippet_desktop_invisible")
        ) {
            const isMobilePreview = isMobileView(editingEl);
            const isMobileHidden = editingEl.classList.contains("o_snippet_mobile_invisible");
            if (isMobilePreview === isMobileHidden) {
                // If the preview mode and the hidden type are the same, the
                // element is considered as hidden.
                show = false;
            }
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
