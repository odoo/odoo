import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class PopupVisibilityPlugin extends Plugin {
    static id = "popupVisibilityPlugin";
    static dependencies = ["visibility"];
    static shared = ["onTargetShow", "onTargetHide"];

    resources = {
        target_show: this.onTargetShow.bind(this),
        target_hide: this.onTargetHide.bind(this),
        clean_for_save_handlers: this.cleanForSave.bind(this),
    };

    setup() {
        this.addDomListener(this.editable, "click", (ev) => {
            // Note: links are excluded here so that internal modal buttons do
            // not close the popup as we want to allow edition of those buttons.
            if (ev.target.matches(".s_popup .js_close_popup:not(a, .btn)")) {
                ev.stopPropagation();
                const popupEl = ev.target.closest(".s_popup");
                this.onTargetHide(popupEl);
                this.dependencies.visibility.onOptionVisibilityUpdate(popupEl, false);
            }
        });
    }

    onTargetShow(target) {
        // Check if the popup is within the editable, because it is cloned on
        // save (see save plugin) and Bootstrap moves it if it is not within the
        // document (see Bootstrap Modal's _showElement).
        if (target.matches(".s_popup") && this.editable.contains(target)) {
            this.window.Modal.getOrCreateInstance(target.querySelector(".modal")).show();
        }
    }

    onTargetHide(target) {
        if (target.matches(".s_popup")) {
            this.window.Modal.getOrCreateInstance(target.querySelector(".modal")).hide();
        }
    }

    cleanForSave({ root }) {
        for (const modalEl of root.querySelectorAll(".s_popup .modal.show")) {
            modalEl.parentElement.dataset.invisible = "1";
            // Do not call .hide() directly, because it is queued whereas
            // .dispose() is not.
            modalEl.classList.remove("show");
            this.window.Modal.getOrCreateInstance(modalEl)._hideModal();
            this.window.Modal.getInstance(modalEl).dispose();
        }
    }
}

registry.category("website-plugins").add(PopupVisibilityPlugin.id, PopupVisibilityPlugin);
