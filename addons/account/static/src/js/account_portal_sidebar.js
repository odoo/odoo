odoo.define('account.AccountPortalSidebar.instance', function (require) {
"use strict";

require('web.dom_ready');
var AccountPortalSidebar = require('account.AccountPortalSidebar');

if (!$('.o_portal_invoice_sidebar').length) {
    return $.Deferred().reject("DOM doesn't contain '.o_portal_invoice_sidebar'");
}

var account_portal_sidebar = new AccountPortalSidebar();
return account_portal_sidebar.attachTo($('.o_portal_invoice_sidebar')).then(function () {
    return account_portal_sidebar;
});
});

//==============================================================================

odoo.define('account.AccountPortalSidebar', function (require) {
"use strict";

var PortalSidebar = require('portal.PortalSidebar');

var AccountPortalSidebar = PortalSidebar.extend({
    events: {
        'click .o_portal_invoice_print': '_onPrintInvoice',
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        this._super.apply(this, arguments);
        var $invoiceHtml = this.$el.find('iframe#invoice_html');
        var updateIframeSize = self._updateIframeSize.bind(self, $invoiceHtml);
        $invoiceHtml.on('load', updateIframeSize);
        $(window).on('resize', updateIframeSize);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the iframe is loaded or the window is resized on customer portal.
     * The goal is to expand the iframe height to display the full report without scrollbar.
     *
     * @private
     * @param {object} $el: the iframe
     */
    _updateIframeSize: function ($el) {
        var $wrapwrap = $el.contents().find('div#wrapwrap');
        // Set it to 0 first to handle the case where scrollHeight is too big for its content.
        $el.height(0);
        $el.height($wrapwrap[0].scrollHeight);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onPrintInvoice: function (ev) {
        ev.preventDefault();
        var href = $(ev.currentTarget).attr('href');
        this._printIframeContent(href);
    },
});


return AccountPortalSidebar;
});
