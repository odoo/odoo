odoo.define('web.assets.qweb', function (require) {
"use strict";

const {assets} = require('@web/core/assets');

const loadXML = assets.loadXML;
assets.loadXML = function (xml, app) {
    loadXML(xml, app);

    const doc = new DOMParser().parseFromString(xml, "text/xml");
    const qwebTemplates = document.createElement("templates");
    for (const element of doc.querySelectorAll("templates > [t-name]:not([owl]), templates > [t-extend]:not([owl])")) {
        qwebTemplates.appendChild(element);
    }

    // don't use require to apply the patch before the first template loading.
    odoo.ready('web.core').then(function () {
        const core = odoo.__DEBUG__.services['web.core'];
        core.qweb.add_template(qwebTemplates);
    });
}

});
