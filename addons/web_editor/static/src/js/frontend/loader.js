odoo.define('web_editor.loader', function (require) {
'use strict';

var ajax = require('web.ajax');

let wysiwygPromise = {};

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
    const Wysiwyg = await getWysiwygClass(options, additionnalAssets);
    return new Wysiwyg(parent, options);
};

async function getWysiwygClass(options, additionnalAssets = []) {
    const wysiwygAlias = options.wysiwygAlias || 'web_editor.wysiwyg';
    if (!wysiwygPromise[wysiwygAlias]) {
        wysiwygPromise[wysiwygAlias] = new Promise(async (resolve) => {
            if (odoo.__DEBUG__.services[wysiwygAlias]) {
                return resolve();
            }
            await loadWysiwyg(additionnalAssets);
            // Wait the loading of the service and his dependencies (use string to
            // avoid parsing of require function).
            const stringFunction = `return new Promise(resolve => {
                odoo.define('${wysiwygAlias}.loaded', require => {
                    ` + 'require' + `('${wysiwygAlias}');
                    resolve();
                });
            });`;
            await new Function(stringFunction)();
            resolve();
        });
    }
    await wysiwygPromise[wysiwygAlias];
    return odoo.__DEBUG__.services[wysiwygAlias];
}
exports.getWysiwygClass = getWysiwygClass;

exports.loadFromTextarea = async (parent, textarea, options) => {
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
    const wysiwyg = await exports.createWysiwyg(parent, currentOptions);

    const $wysiwygWrapper = $textarea.closest('.o_wysiwyg_textarea_wrapper');
    const $form = $textarea.closest('form');

    // hide and append the $textarea in $form so it's value will be send
    // through the form.
    $textarea.hide();
    $form.append($textarea);
    $wysiwygWrapper.html('');

    await wysiwyg.appendTo($wysiwygWrapper);
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
