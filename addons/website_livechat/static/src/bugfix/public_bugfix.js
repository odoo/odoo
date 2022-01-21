/**
 * This file allows introducing new JS modules without contaminating other files.
 * This is useful when bug fixing requires adding such JS modules in stable
 * versions of Odoo. Any module that is defined in this file should be isolated
 * in its own file in master.
 */
odoo.define('website_livechat/static/src/bugfix/bugfix.js', function (require) {
'use strict';

const { LivechatButton } = require('im_livechat.legacy.im_livechat.im_livechat');

LivechatButton.include({
    className: `${LivechatButton.prototype.className} o_bottom_fixed_element`,

    /**
     * @override
     */
    start() {
        // We trigger a resize to launch the event that checks if this element hides
        // a button when the page is loaded.
        $(window).trigger('resize');
        return this._super(...arguments);
    },
});
});
