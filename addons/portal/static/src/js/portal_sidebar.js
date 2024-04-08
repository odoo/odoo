/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import { deserializeDateTime } from "@web/core/l10n/dates";

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
        const sidebarTimeago = this.el.querySelectorAll('.o_portal_sidebar_timeago');
        sidebarTimeago.forEach((el) => {
            const dateTime = deserializeDateTime(el.getAttribute('datetime'));
            const today = DateTime.now().startOf('day');
            const diff = dateTime.diff(today).as("days");
            let displayStr;

                if (diff === 0) {
                    displayStr = _t('Due today');
                } else if (diff > 0) {
                    // Workaround: force uniqueness of these two translations. We use %1d because the string
                    // with %d is already used in mail and mail's translations are not sent to the frontend.
                    displayStr = _t('Due in %s days', Math.abs(diff).toFixed(1));
                } else {
                    displayStr = _t('%s days overdue', Math.abs(diff).toFixed(1));
                }
                el.textContent = displayStr;
        });
    },
    /**
     * @private
     * @param {string} href
     */
    _printIframeContent: function (href) {
        debugger;
        if (!this.printContent) {
            const iframe = document.createElement('iframe');
            iframe.setAttribute('id', 'print_iframe_content');
            iframe.setAttribute('src', href);
            iframe.setAttribute('style', 'display:none');
            // TODO: MSH: printContent seems jquery element, need to check
            this.el.appendChild(this.printContent);
            this.printContent.addEventListener('load', function () {
                // TODO: MSH: To test and convert
                $(this).get(0).contentWindow.print();
            });
        } else {
            // TODO: MSH: To test and convert
            this.printContent.get(0).contentWindow.print();
        }
    },
});
export default PortalSidebar;
