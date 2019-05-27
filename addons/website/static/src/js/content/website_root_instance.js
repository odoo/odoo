odoo.define('root.widget', function (require) {
'use strict';

require('web.dom_ready');
var websiteRootData = require('website.root');

var websiteRoot = new websiteRootData.WebsiteRoot(null);
return websiteRoot.attachTo(document.body).then(function () {
    return websiteRoot;
});
});
