odoo.define('web.RendererWrapper', function (require) {
    "use strict";

    const { ComponentWrapper } = require('web.OwlCompatibility');

    class RendererWrapper extends ComponentWrapper {
        getLocalState() { }
        setLocalState() { }
        giveFocus() { }
        resetLocalState() { } 
    }

    return RendererWrapper;

});
