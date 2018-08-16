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
        $invoiceHtml.on('load', self._onLoadIframe.bind(self, $invoiceHtml));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the iframe is load on custome portal
     * here we set height and width of html preview (iframe)
     *
     * @private
     */
    _onLoadIframe: function ($el) {
        var $body = $el.contents().find('body');
        // expand iframe height for display full report on the custome portal (no scrollbar in iframe)
        $el.height($body.scrollParent().height());
        // removed extra space in html preview (specially left and right margin)
        $body.width('100%');
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
