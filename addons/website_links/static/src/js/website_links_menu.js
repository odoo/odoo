/**
 * The purpose of this script is to copy the current URL of the website
 * into the URL form of the URL shortener (module website_links)
 * when the user clicks the link "Share this page" on top of the page.
 */

odoo.define('website_links.website_links_menu', function (require) {
'use strict';

var sAnimations = require('website.content.snippets.animation');

sAnimations.registry.websiteLinksMenu = sAnimations.Class.extend({
	selector: '#o_website_links_share_page',

	/**
     * @override
     */
    start: function () {
        this.$el.attr('href', '/r?u=' + encodeURIComponent(window.location.href));
        return this._super.apply(this, arguments);
    },
});
});
