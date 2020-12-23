odoo.define('web_editor.loader', function (require) {
'use strict';

var Wysiwyg = require('web_editor.wysiwyg.root');

function load(parent, textarea, options) {
    var loading = textarea.nextElementSibling;
    if (loading && !loading.classList.contains('o_wysiwyg_loading')) {
        loading = null;
    }

    if (!textarea.value.match(/\S/)) {
        textarea.value = '<p><br/></p>';
    }

    var wysiwyg = new Wysiwyg(parent, options);
    return wysiwyg.attachTo(textarea).then(() => {
        if (loading) {
            loading.parentNode.removeChild(loading);
        }
        return wysiwyg;
    });
}

return {
    load: load,
};
});
