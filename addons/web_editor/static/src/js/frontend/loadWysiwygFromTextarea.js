/** @odoo-module **/

import { loadBundle } from "@web/core/assets";
import { attachComponent } from '@web/legacy/utils';

export async function loadWysiwygFromTextarea(parent, textarea, options) {
    var loading = textarea.nextElementSibling;
    if (loading && !loading.classList.contains('o_wysiwyg_loading')) {
        loading = null;
    }
    const $textarea = $(textarea);
    const currentOptions = Object.assign({}, options);
    currentOptions.value = currentOptions.value || $textarea.val() || '';
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

    const $wysiwygWrapper = $textarea.closest('.o_wysiwyg_textarea_wrapper');
    const $form = $textarea.closest('form');

    // hide and append the $textarea in $form so it's value will be send
    // through the form.
    $textarea.hide();
    $form.append($textarea);
    $wysiwygWrapper.html('');
    const wysiwygWrapper = $wysiwygWrapper[0];
    await attachComponent(parent, wysiwygWrapper, LegacyWysiwyg, {
        options: currentOptions,
        editingValue: currentOptions.value,
    });

    $form.find('.note-editable').data('wysiwyg', wysiwyg);

    // o_we_selected_image has not always been removed when
    // saving a post so we need the line below to remove it if it is present.
    $form.find('.note-editable').find('img.o_we_selected_image').removeClass('o_we_selected_image');

    let b64imagesPending = true;
    $form.on('click', 'button[type=submit]', (ev) => {
        if (b64imagesPending) {
            ev.preventDefault();
            wysiwyg.savePendingImages().finally(() => {
                b64imagesPending = false;
                ev.currentTarget.click();
            });
        } else {
            $form.find('.note-editable').find('img.o_we_selected_image').removeClass('o_we_selected_image');
            // float-start class messes up the post layout OPW 769721
            $form.find('.note-editable').find('img.float-start').removeClass('float-start');
            $textarea.html(wysiwyg.getValue());
        }
    });

    return wysiwyg;
};
