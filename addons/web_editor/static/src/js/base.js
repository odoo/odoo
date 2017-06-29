odoo.define('web_editor.base', function (require) {
'use strict';

var ajax = require('web.ajax');
var session = require('web.session');

var domReady = $.Deferred();
$(domReady.resolve.bind(domReady));

return {
    /**
     * If a widget needs to be instantiated on page loading, it needs to wait
     * for appropriate resources to be loaded. This function returns a Deferred
     * which is resolved when the dom is ready, the session is bound
     * (translations loaded) and the XML is loaded. This should however not be
     * necessary anymore as widgets should not be parentless and should then be
     * instantiated (directly or not) by the page main component (webclient,
     * website root, editor bar, ...). The DOM will be ready then, the main
     * component is in charge of waiting for the session and the XML can be
     * lazy loaded thanks to the @see Widget.xmlDependencies key.
     *
     * @returns {Deferred}
     */
    ready: function () {
        return $.when(domReady, session.is_bound, ajax.loadXML());
    },
};
});

//==============================================================================

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

//==============================================================================

odoo.define('web_editor.ready', function (require) {
'use strict';

var base = require('web_editor.base');

return base.ready();
});
