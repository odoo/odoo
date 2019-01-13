odoo.define('portal.PortalSidebar', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var Widget = require('web.Widget');
var time = require('web.time');

var _t = core._t;

var PortalSidebar = Widget.extend({
    /**
     * @override
     */
    start: function () {
        var self = this;
        this._super.apply(this, arguments);
        this._setDelayLabel();
    },

    //--------------------------------------------------------------------------
    // Private
    //---------------------------------------------------------------------------

    /**
     * Set the due/delay information according to the given date
     * like : <span class="o_portal_sidebar_timeago" t-att-datetime="invoice.date_due"/>
     * @private
     */
    _setDelayLabel : function () {
        var $sidebarTimeago = this.$el.find('.o_portal_sidebar_timeago');
        _.each($sidebarTimeago, function (el) {
            var dateTime = moment(time.auto_str_to_date($(el).attr('datetime'))),
                today = moment().startOf('day'),
                diff = dateTime.diff(today, 'days', true),
                displayStr;

            if (diff === 0){
                displayStr = _t('Due today');
            } else if (diff > 0) {
                displayStr = _.str.sprintf(_t('Due in %d days'), Math.abs(diff));
            } else {
                displayStr = _.str.sprintf(_t('%d days overdue'), Math.abs(diff));
            }
             $(el).text(displayStr);
        });
    },
    /**
     * @private
     * @param {string} href
     */
    _printIframeContent: function (href) {
        // due to this issue : https://bugzilla.mozilla.org/show_bug.cgi?id=911444
        // open a new window with pdf for print in Firefox (in other system: http://printjs.crabbly.com)
        if ($.browser.mozilla) {
            window.open(href, '_blank');
            return ;
        }
        if (!this.printContent) {
            this.printContent = $('<iframe id="print_iframe_content" src="'+ href +'" style="display:none"></iframe>');
            this.$el.append(this.printContent);
            this.printContent.on('load', function () {
                $(this).get(0).contentWindow.print();
            });
        } else {
            this.printContent.get(0).contentWindow.print();
        }
    },
});
return PortalSidebar;
});
