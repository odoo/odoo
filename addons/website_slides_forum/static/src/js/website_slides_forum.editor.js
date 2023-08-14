odoo.define('website_slides_forum.editor', function (require) {
"use strict";

var core = require('web.core');
var QWeb = core.qweb;
var WebsiteNewMenu = require('website.newMenu');

 WebsiteNewMenu.include({
    xmlDependencies: WebsiteNewMenu.prototype.xmlDependencies.concat(
        ['/website_slides_forum/static/src/xml/website_slides_forum_channel.xml']
    ),
});
});
