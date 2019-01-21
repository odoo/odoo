odoo.define('web_editor.base', function (require) {
'use strict';

var ajax = require('web.ajax');
var session = require('web.session');

var domReady = $.Deferred();
$(domReady.resolve.bind(domReady));

return {
    /**
     * If a widget needs to be instantiated on page loading, it needs to wait
     * for appropriate resources in order to be loaded. This function returns a
     * Deferred that is resolved when the dom is ready, the session is bound
     * (translations loaded) and the XML is loaded. This should however not be
     * necessary anymore as widgets should not be parentless and should then be
     * instantiated (directly or not) by the page's main component (webclient,
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
