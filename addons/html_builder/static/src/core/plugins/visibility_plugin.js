import { Plugin } from "@html_editor/plugin";
import { isMobileView } from "@html_builder/utils/utils";

export class VisibilityPlugin extends Plugin {
    static id = "visibility";
    static shared = [
        "toggleTargetVisibility",
        "cleanForSaveVisibility",
        "hideInvisibleEl",
        "showInvisibleEl",
    ];

    resources = {
        on_option_visibility_update: onOptionVisibilityUpdate,
        on_mobile_preview_clicked: this.onMobilePreviewClicked.bind(this),
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
            const show = isMobilePreview != isMobileHidden;
            onOptionVisibilityUpdate({ editingEl: invisibleOverrideEl, show: show });
        }
    }

    toggleTargetVisibility(editingEl, show) {
        show = onOptionVisibilityUpdate({ editingEl: editingEl, show: show });
        const dispatchName = show ? "target_show" : "target_hide";
        this.dispatchTo(dispatchName, editingEl);
        return show;
    }

    hideInvisibleEl(snippetEl) {
        snippetEl.classList.remove("o_snippet_override_invisible");
    }

    showInvisibleEl(snippetEl) {
        const isMobilePreview = isMobileView(snippetEl);
        const isMobileHidden = snippetEl.classList.contains("o_snippet_mobile_invisible");
        const isDesktopHidden = snippetEl.classList.contains("o_snippet_desktop_invisible");
        if ((isMobileHidden && isMobilePreview) || (isDesktopHidden && !isMobilePreview)) {
            snippetEl.classList.add("o_snippet_override_invisible");
        }
    }
}

function isTargetVisible(editingEl) {
    return editingEl.dataset.invisible !== "1";
}

function onOptionVisibilityUpdate({ editingEl, show }) {
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
