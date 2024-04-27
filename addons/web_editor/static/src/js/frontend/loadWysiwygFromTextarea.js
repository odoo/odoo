/** @odoo-module **/

import { loadBundle } from "@web/core/assets";
import { attachComponent } from '@web/legacy/utils';

export async function loadWysiwygFromTextarea(parent, textarea, options) {
    debugger;
    var loading = textarea.nextElementSibling;
    if (loading && !loading.classList.contains('o_wysiwyg_loading')) {
        loading = null;
    }
    const currentOptions = Object.assign({}, options);
    currentOptions.value = currentOptions.value || textarea.value || '';
    if (!currentOptions.value.trim()) {
        currentOptions.value = '<p><br></p>';
    }

    await loadBundle("web_editor.assets_wysiwyg");
    const { Wysiwyg } = await odoo.loader.modules.get('@web_editor/js/wysiwyg/wysiwyg');
    let wysiwyg;
    class LegacyWysiwyg extends Wysiwyg {
        constructor(...args) {
            super(...args);
            wysiwyg = this;
        }
    }

    const wysiwygWrapper = textarea.closest('.o_wysiwyg_textarea_wrapper');
    const form = textarea.closest('form');

    // hide and append the $textarea in $form so it's value will be send
    // through the form.
    textarea.style.display = 'none';
    form.append(textarea);
    const wysiwygWrapperHTML = wysiwygWrapper.innerHTML
    await attachComponent(parent, wysiwygWrapperHTML, LegacyWysiwyg, {
        options: currentOptions,
        editingValue: currentOptions.value,
    });

    const editableEL = form.querySelector('.note-editable');
    editableEL.dataset.wysiwyg = wysiwyg;

    // o_we_selected_image has not always been removed when
    // saving a post so we need the line below to remove it if it is present.
    editableEL.querySelector('img.o_we_selected_image').classList.remove('o_we_selected_image');

    let b64imagesPending = true;
    form.querySelector('button[type=submit]').addEventListener('click', (ev) => {
        if (b64imagesPending) {
            ev.preventDefault();
            wysiwyg.savePendingImages().finally(() => {
                b64imagesPending = false;
                ev.currentTarget.click();
            });
        } else {
            editableEL.querySelectorAll('img.o_we_selected_image').forEach(img => img.classList.remove('o_we_selected_image'));
            // float-start class messes up the post layout OPW 769721
            editableEL.querySelectorAll('img.float-start').forEach(img => img.classList.remove('float-start'));
            textarea.innerHTML = wysiwyg.getValue();
        }
    });

    return wysiwyg;
};
