odoo.define('web_editor.loader', function (require) {
'use strict';

const { getBundle, loadBundle } = require('@web/core/assets');

const exports = {};

async function loadWysiwyg(additionnalAssets=[]) {
    const xmlids = ['web_editor.assets_wysiwyg', ...additionnalAssets];
    for (const xmlid of xmlids) {
        const assets = await getBundle(xmlid);
        await loadBundle(assets);
    }
}
exports.loadWysiwyg = loadWysiwyg;

/**
 * Load the assets and create a wysiwyg.
 *
 * @param {Widget} parent The wysiwyg parent
 * @param {object} options
 * @param {object} options.wysiwygOptions The wysiwyg options
 * @param {string} options.moduleName The wysiwyg module name
 * @param {object} options.additionnalAssets The additional assets
 */
exports.createWysiwyg = async (parent, options = {}) => {
    const Wysiwyg = await getWysiwygClass(options);
    return new Wysiwyg(parent, options.wysiwygOptions);
};

async function getWysiwygClass({moduleName = 'web_editor.wysiwyg', additionnalAssets = []} = {}) {
    if (!(await odoo.ready(moduleName))) {
        await loadWysiwyg(additionnalAssets);
        await odoo.ready(moduleName);
    }
    return odoo.__DEBUG__.services[moduleName];
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

    const Wysiwyg = await getWysiwygClass();
    const wysiwyg = new Wysiwyg(parent, currentOptions);

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
        // float-start class messes up the post layout OPW 769721
        $form.find('.note-editable').find('img.float-start').removeClass('float-start');
        $textarea.html(wysiwyg.getValue());
    });

    return wysiwyg;
};

return exports;
});
