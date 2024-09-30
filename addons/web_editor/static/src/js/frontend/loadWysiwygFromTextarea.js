/** @odoo-module **/

import { loadBundle } from "@web/core/assets";
import { ensureJQuery } from "@web/core/ensure_jquery";
import { attachComponent } from "@web_editor/js/core/owl_utils";

export async function loadWysiwygFromTextarea(parentEl, textareaEl, options) {
    let loading = textareaEl.nextElementSibling;
    if (loading && !loading.classList.contains('o_wysiwyg_loading')) {
        loading = null;
    }
    const currentOptions = Object.assign({}, options);
    currentOptions.value = currentOptions.value || textareaEl.value || "";
    if (!currentOptions.value.trim()) {
        currentOptions.value = '<p><br></p>';
    }

    await ensureJQuery();
    await loadBundle("web_editor.assets_wysiwyg");
    const { Wysiwyg } = await odoo.loader.modules.get('@web_editor/js/wysiwyg/wysiwyg');
    let wysiwyg;
    class LegacyWysiwyg extends Wysiwyg {
        constructor(...args) {
            super(...args);
            wysiwyg = this;
        }
    }

    const wysiwygWrapperEl = textareaEl.closest(".o_wysiwyg_textarea_wrapper");
    const formEl = textareaEl.closest("form");

    // hide and append the $textarea in $form so it's value will be send
    // through the form.
    textareaEl.style.display = "none";
    formEl?.append(textareaEl);
    wysiwygWrapperEl.innerHTML = "";
    await attachComponent(parentEl, wysiwygWrapperEl, LegacyWysiwyg, {
        options: currentOptions,
        editingValue: currentOptions.value,
    });

    const editableEL = formEl?.querySelector(".note-editable");
    if (editableEL) {
        editableEL.dataset.wysiwyg = wysiwyg;

        // o_we_selected_image has not always been removed when
        // saving a post so we need the line below to remove it if it is present.
        editableEL.querySelectorAll("img.o_we_selected_image").forEach((imgEl) => {
            imgEl.classList.remove("o_we_selected_image");
        });
    }

    let b64imagesPending = true;
    formEl?.querySelector("button[type=submit]").addEventListener("click", (ev) => {
        if (b64imagesPending) {
            ev.preventDefault();
            wysiwyg.savePendingImages().finally(() => {
                b64imagesPending = false;
                ev.target?.click();
            });
        } else {
            editableEL
                ?.querySelectorAll("img.o_we_selected_image")
                .forEach((img) => img.classList.remove("o_we_selected_image"));
            editableEL
                ?.querySelectorAll("img.float-start")
                .forEach((img) => img.classList.remove("float-start"));
            textareaEl.innerHTML = wysiwyg.getValue();
        }
    });

    return wysiwyg;
};
