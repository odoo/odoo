/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import { deserializeDate } from "@web/core/l10n/dates";

const { DateTime } = luxon;

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
            var dateTime = deserializeDate($(el).attr('datetime')).startOf('day'),
                today = DateTime.now().startOf('day'),
                diff = dateTime.diff(today).as("days"),
                displayStr;

                if (diff === 0) {
                    displayStr = _t('Due today');
                } else if (diff > 0) {
                    // Workaround: force uniqueness of these two translations. We use %1d because the string
                    // with %d is already used in mail and mail's translations are not sent to the frontend.
                    displayStr = _t('Due in %s days', Math.abs(diff).toFixed());
                } else {
                    displayStr = _t('%s days overdue', Math.abs(diff).toFixed());
                }
                $(el).text(displayStr);
        });
    },
    /**
     * @private
     * @param {string} href
     */
    _printIframeContent: function (href) {
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
