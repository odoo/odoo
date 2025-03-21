import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class PopupOptionPlugin extends Plugin {
    static id = "PopupOption";
    static dependencies = ["anchor", "visibility"];

    resources = {
        builder_options: [
            {
                template: "html_builder.PopupOption",
                selector: ".s_popup",
                exclude: "#website_cookies_bar",
                applyTo: ".modal",
            },
            {
                template: "html_builder.PopupCookiesOption",
                selector: ".s_popup#website_cookies_bar",
                applyTo: ".modal",
            },
        ],
        dropzone_selector: {
            selector: ".s_popup",
            exclude: "#website_cookies_bar",
            dropIn: ":not(p).oe_structure:not(.oe_structure_solo):not([data-snippet] *), :not(.o_mega_menu):not(p)[data-oe-type=html]:not([data-snippet] *)",
        },
        builder_actions: this.getActions(),
        on_cloned_handlers: this.onCloned.bind(this),
        on_add_element_handlers: this.onAddElement.bind(this),
        target_show: this.onTargetShow.bind(this),
        target_hide: this.onTargetHide.bind(this),
        clean_for_save_handlers: this.cleanForSave.bind(this),
    };

    setup() {
        this.window = this.document.defaultView;

        this.addDomListener(this.editable, "pointerdown", (ev) => {
            // Note: links are excluded here so that internal modal buttons do
            // not close the popup as we want to allow edition of those buttons.
            if (ev.target.matches(".s_popup .js_close_popup:not(a, .btn)")) {
                ev.stopPropagation();
                const popupEl = ev.target.closest(".s_popup");
                this.dependencies.visibility.toggleTargetVisibility(popupEl, false);
                this.dispatchTo("update_invisible_panel", popupEl);
                // Avoid selecting the snippet beneath the popup.
                this.addDomListener(this.window, "pointerup", (ev) => ev.stopPropagation(), {
                    once: true,
                    capture: true,
                });
            }
        });
    }

    getActions() {
        return {
            // Moves the snippet in #o_shared_blocks to be common to all pages
            // or inside the first editable oe_structure in the main to be on
            // current page only.
            moveBlock: {
                isApplied: ({ editingElement, value }) =>
                    editingElement.closest("#o_shared_blocks")
                        ? value === "allPages"
                        : value === "currentPage",
                apply: ({ editingElement, value }) => {
                    const selector =
                        value === "allPages" ? "#o_shared_blocks" : "main .oe_structure.o_editable";
                    const whereEl = this.editable.querySelector(selector);
                    const popupEl = editingElement.closest(".s_popup");
                    whereEl.insertAdjacentElement("afterbegin", popupEl);
                },
            },
            setBackdrop: {
                isApplied: ({ editingElement }) => {
                    const hasBackdropColor =
                        editingElement.style.getPropertyValue("background-color").trim() ===
                        "var(--black-50)";
                    const hasNoBackdropClass =
                        editingElement.classList.contains("s_popup_no_backdrop");
                    return hasBackdropColor && !hasNoBackdropClass;
                },
                apply: ({ editingElement }) => {
                    editingElement.classList.remove("s_popup_no_backdrop");
                    editingElement.style.setProperty(
                        "background-color",
                        "var(--black-50)",
                        "important"
                    );
                },
                clean: ({ editingElement }) => {
                    editingElement.classList.add("s_popup_no_backdrop");
                    editingElement.style.removeProperty("background-color");
                },
            },
            copyAnchor: {
                apply: ({ editingElement }) => {
                    this.dependencies.anchor.createOrEditAnchorLink(
                        editingElement.closest(".s_popup")
                    );
                },
            },
        };
    }

    onCloned({ cloneEl }) {
        if (cloneEl.matches(".s_popup")) {
            this.assignUniqueID(cloneEl);
        }
    }

    onAddElement({ elementToAdd }) {
        if (elementToAdd.matches(".s_popup")) {
            this.assignUniqueID(elementToAdd);
            this.window.Modal.getOrCreateInstance(elementToAdd.querySelector(".modal")).show();
        }
    }

    onTargetShow(target) {
        // Check if the popup is within the editable, because it is cloned on
        // save (see save plugin) and Bootstrap moves it if it is not within the
        // document (see Bootstrap Modal's _showElement).
        if (target.matches(".s_popup") && this.editable.contains(target)) {
            const modalEl = target.querySelector(".modal");
            this.window.Modal.getOrCreateInstance(modalEl).show();
            target.classList.remove("d-none");
        }
    }

    onTargetHide(target) {
        if (target.matches(".s_popup")) {
            target.classList.add("d-none");
            this.window.Modal.getOrCreateInstance(target.querySelector(".modal")).hide();
        }
    }

    cleanForSave({ root }) {
        for (const modalEl of root.querySelectorAll(".s_popup .modal.show")) {
            modalEl.parentElement.dataset.invisible = "1";
            // Do not call .hide() directly, because it is queued whereas
            // .dispose() is not.
            this.window.Modal.getOrCreateInstance(modalEl)._hideModal();
            this.window.Modal.getInstance(modalEl).dispose();
        }
    }

    assignUniqueID(editingElement) {
        editingElement.closest(".s_popup").id = `sPopup${Date.now()}`;
    }
}

registry.category("website-plugins").add(PopupOptionPlugin.id, PopupOptionPlugin);
