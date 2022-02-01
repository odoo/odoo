odoo.define('website.seo', function (require) {
'use strict';

var Dialog = require('web.Dialog');
var websiteNavbarData = require('website.navbar');

var SeoConfigurator = Dialog.extend({});

var SeoMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({});

return {
    SeoConfigurator: SeoConfigurator,
    SeoMenu: SeoMenu,
};
});
