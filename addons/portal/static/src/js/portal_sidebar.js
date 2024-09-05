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
        const sidebarTimeagoEls = this.el.querySelectorAll(".o_portal_sidebar_timeago");
        sidebarTimeagoEls.forEach((el) => {
            const dateTime = deserializeDateTime(el.getAttribute("datetime"));
            const today = DateTime.now().startOf("day");
            const diff = dateTime.diff(today).as("days");
            let displayStr;

                if (diff === 0) {
                    displayStr = _t('Due today');
                } else if (diff > 0) {
                    // Workaround: force uniqueness of these two translations. We use %1d because the string
                    // with %d is already used in mail and mail's translations are not sent to the frontend.
                    displayStr = _t('Due in %s days', Math.abs(diff).toFixed());
                } else {
                    displayStr = _t('%s days overdue', Math.abs(diff).toFixed());
                }
                el.textContent = displayStr;
        });
    },
    /**
     * @private
     * @param {string} href
     */
    _printIframeContent: function (href) {
        if (!this.printContent) {
            this.printContent = document.createElement("iframe");
            this.printContent.setAttribute("id", "print_iframe_content");
            this.printContent.setAttribute("src", href);
            this.printContent.setAttribute("style", "display:none");
            this.el.appendChild(this.printContent);
            this.printContent.addEventListener("load", function () {
                this.contentWindow.print();
            });
        } else {
            this.printContent.contentWindow.print();
        }
    },
});
export default PortalSidebar;
