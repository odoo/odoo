/** @odoo-module alias=portal.PortalSidebar **/

import publicWidget from "web.public.widget";
import time from "web.time";
import session from "web.session";
import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";

var PortalSidebar = publicWidget.Widget.extend({
    /**
     * @override
     */
    start: function () {
        this._setDelayLabel();
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //---------------------------------------------------------------------------

    /**
     * Set the due/delay information according to the given date
     * like : <span class="o_portal_sidebar_timeago" t-att-datetime="invoice.date_due"/>
     *
     * @private
     */
    _setDelayLabel: function () {
        var $sidebarTimeago = this.$el.find('.o_portal_sidebar_timeago').toArray();
        $sidebarTimeago.forEach((el) => {
            var dateTime = moment(time.auto_str_to_date($(el).attr('datetime'))),
                today = moment().startOf('day'),
                diff = dateTime.diff(today, 'days', true),
                displayStr;

            session.is_bound.then(function (){
                if (diff === 0) {
                    displayStr = _t('Due today');
                } else if (diff > 0) {
                    // Workaround: force uniqueness of these two translations. We use %1d because the string
                    // with %d is already used in mail and mail's translations are not sent to the frontend.
                    displayStr = sprintf(_t('Due in %s days'), Math.abs(diff).toFixed(1));
                } else {
                    displayStr = sprintf(_t('%s days overdue'), Math.abs(diff).toFixed(1));
                }
                $(el).text(displayStr);
            });
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
            return;
        }
        if (!this.printContent) {
            this.printContent = $('<iframe id="print_iframe_content" src="' + href + '" style="display:none"></iframe>');
            this.$el.append(this.printContent);
            this.printContent.on('load', function () {
                $(this).get(0).contentWindow.print();
            });
        } else {
            this.printContent.get(0).contentWindow.print();
        }
    },
});
export default PortalSidebar;
