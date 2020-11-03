odoo.define('web_editor.loader', function (require) {
'use strict';

var ajax = require('web.ajax');

let wysiwygPromise;

/**
 * Load the assets and create a wysiwyg.
 *
 * @param {Widget} parent The wysiwyg parent
 * @param {object} options The wysiwyg options
 */
async function createWysiwyg(parent, options, additionnalAssets = []) {
    if (!wysiwygPromise) {
        wysiwygPromise = new Promise(async (resolve) => {
            await ajax.loadLibs({assetLibs: ['web_editor.compiled_assets_wysiwyg', ...additionnalAssets]});
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
}

async function loadFromTextarea(parent, textarea, options) {
    var loading = textarea.nextElementSibling;
    if (loading && !loading.classList.contains('o_wysiwyg_loading')) {
        loading = null;
    }
    const $textarea = $(textarea);
    const currentOptions = Object.assign({}, options);
    if (!currentOptions.value || !currentOptions.value.trim()) {
        currentOptions.value = '<p><br><p>';
    }
    const wysiwyg = await createWysiwyg(parent, currentOptions);

    const $wysiwygWrapper = $textarea.closest('.o_wysiwyg_wrapper');
    const $form = $textarea.closest('form');
    $wysiwygWrapper.css({
        'display': 'flex',
        'flex-direction': 'column',
        'flex-grow': '1 1 auto',
        'height': options.height || 200,
    });

    // hide and append the $textarea in $form so it's value will be send
    // through the form.
    $textarea.hide();
    $form.append($textarea);

    await wysiwyg.attachTo($wysiwygWrapper);
    $form.find('.note-editable').data('wysiwyg', wysiwyg);

    $form.on('click', 'button[type=submit]', async (e) => {
        // float-left class messes up the post layout OPW 769721
        $form.find('.note-editable').find('img.float-left').removeClass('float-left');
        $textarea.val(await wysiwyg.getValue());
    });

    // Remove the loading spinner.
    if (loading) {
        loading.parentNode.removeChild(loading);
    }

    return wysiwyg;
}

return {
    loadFromTextarea: loadFromTextarea,
    createWysiwyg: createWysiwyg,
};
});
