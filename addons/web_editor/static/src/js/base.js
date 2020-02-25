odoo.define('web_editor.base', function (require) {
'use strict';

var ajax = require('web.ajax');
var session = require('web.session');

var domReady = new Promise(function(resolve) {
    $(resolve);
});

return {
    /**
     * If a widget needs to be instantiated on page loading, it needs to wait
     * for appropriate resources to be loaded. This function returns a Promise
     * which is resolved when the dom is ready, the session is bound
     * (translations loaded) and the XML is loaded. This should however not be
     * necessary anymore as widgets should not be parentless and should then be
     * instantiated (directly or not) by the page main component (webclient,
     * website root, editor bar, ...). The DOM will be ready then, the main
     * component is in charge of waiting for the session and the XML can be
     * lazy loaded thanks to the @see Widget.xmlDependencies key.
     *
     * @returns {Promise}
     */
    ready: function () {
        return Promise.all([domReady, session.is_bound, ajax.loadXML()]);
    },
};
});

//==============================================================================

odoo.define('web_editor.context', function (require) {
'use strict';

// TODO this should be re-removed as soon as possible.

function getContext(context) {
    var html = document.documentElement;
    return _.extend({
        lang: (html.getAttribute('lang') || 'en_US').replace('-', '_'),

        // Unfortunately this is a mention of 'website' in 'web_editor' as there
        // was no other way to do it as this was restored in a stable version.
        // Indeed, the editor is currently using this context at the root of JS
        // module, so there is no way for website to hook itself before
        // web_editor uses it (without a risky refactoring of web_editor in
        // stable). As mentioned above, the editor should not use this context
        // anymore anyway (this was restored by the saas-12.2 editor revert).
        'website_id': html.getAttribute('data-website-id') | 0,
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
