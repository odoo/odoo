odoo.define('web_editor.loader', function (require) {
'use strict';

var ajax = require('web.ajax');

let wysiwygPromise;

const exports = {};

function loadWysiwyg(additionnalAssets=[]) {
    return ajax.loadLibs({assetLibs: ['web_editor.compiled_assets_wysiwyg', ...additionnalAssets]}, undefined, '/web_editor/public_render_template');
}
exports.loadWysiwyg = loadWysiwyg;

/**
 * Load the assets and create a wysiwyg.
 *
 * @param {Widget} parent The wysiwyg parent
 * @param {object} options The wysiwyg options
 */
exports.createWysiwyg = async (parent, options, additionnalAssets = []) => {
    if (!wysiwygPromise) {
        wysiwygPromise = new Promise(async (resolve) => {
            await loadWysiwyg(additionnalAssets);
            // Wait the loading of the service and his dependencies (use string to
            // avoid parsing of require function).
            const stringFunction = `return new Promise(resolve => {
                odoo.define('web_editor.wysiwig.loaded', require => {
                    ` + 'require' + `('web_editor.wysiwyg');
                    resolve();
                });
            });`;
            await new Function(stringFunction)();
            resolve();
        });
    }
    await wysiwygPromise;
    const Wysiwyg = odoo.__DEBUG__.services['web_editor.wysiwyg'];
    return new Wysiwyg(parent, options);
};

exports.loadFromTextarea = async (parent, textarea, options) => {
    const $textarea = $(textarea);
    const $form = $textarea.closest('form');

    const currentOptions = Object.assign({}, options);
    currentOptions.value = currentOptions.value || $textarea.val() || '';
    if (!currentOptions.value.trim()) {
        currentOptions.value = '<p><br></p>';
    }
    const wysiwyg = await exports.createWysiwyg(parent, currentOptions);

    // Instantiate the editor by first creating a special wrapper div after the
    // textarea, adding the editor widget inside then finish by hiding the
    // textarea (leave it there to send is value with the form).
    const wrapperEl = document.createElement('div');
    wrapperEl.classList.add('position-relative', 'o_wysiwyg_textarea_wrapper');
    textarea.after(wrapperEl);
    await wysiwyg.appendTo(wrapperEl);
    textarea.classList.add('d-none');
    $form.find('.note-editable').data('wysiwyg', wysiwyg);

    // o_we_selected_image has not always been removed when
    // saving a post so we need the line below to remove it if it is present.
    $form.find('.note-editable').find('img.o_we_selected_image').removeClass('o_we_selected_image');
    $form.on('click', 'button[type=submit]', (e) => {
        $form.find('.note-editable').find('img.o_we_selected_image').removeClass('o_we_selected_image');
        // float-left class messes up the post layout OPW 769721
        $form.find('.note-editable').find('img.float-left').removeClass('float-left');
        $textarea.html(wysiwyg.getValue());
    });

    return wysiwyg;
};

return exports;
});
