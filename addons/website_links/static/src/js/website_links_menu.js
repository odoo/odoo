/**
 * The purpose of this script is to copy the current URL of the website
 * into the URL form of the URL shortener (module website_links)
 * when the user clicks the link "Share this page" on top of the page.
 */

odoo.define('website_links.website_links_menu', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var websiteNavbarData = require('website.navbar');

const { registry } = require("@web/core/registry");

var WebsiteLinksMenu = publicWidget.Widget.extend({

    /**
     * @override
     */
    start: function () {
        this.$el.attr('href', '/r?u=' + encodeURIComponent(window.location.href));
        return this._super.apply(this, arguments);
    },
});

registry.category("website_navbar_widgets").add("WebsiteLinksMenu", {
    Widget: WebsiteLinksMenu,
    selector: '#o_website_links_share_page',
});

});
