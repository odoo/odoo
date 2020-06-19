odoo.define('root.widget', function (require) {
'use strict';

var lazyloader = require('web.public.lazyloader');
var websiteRootData = require('website.root');

var websiteRoot = new websiteRootData.WebsiteRoot(null);
return lazyloader.allScriptsLoaded.then(function () {
    return websiteRoot.attachTo(document.body).then(function () {
        return websiteRoot;
    });
});
});
