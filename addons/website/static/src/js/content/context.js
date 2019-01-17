odoo.define('web_editor.context', function (require) {
'use strict';

function getContext(context) {
    var html = document.documentElement;
    return _.extend({
        lang: (html.getAttribute('lang') || 'en_US').replace('-', '_'),
    }, context || {});
}

function getExtraContext(context) {
    var html = document.documentElement;
    return _.extend(getContext(), {
        editable: !!(html.dataset.editable || $('[data-oe-model]').length), // temporary hack, this should be done in python
        translatable: !!html.dataset.translatable,
        edit_translations: !!html.dataset.edit_translations,
    }, context || {});
}

return {
    get: getContext,
    getExtra: getExtraContext,
};
});
