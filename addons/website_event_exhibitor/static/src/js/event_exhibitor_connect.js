/** @odoo-module **/

import { debounce } from "@web/core/utils/timing";
import publicWidget from "@web/legacy/js/public/public_widget";
import { redirect } from "@web/core/utils/urls";
import { ExhibitorConnectClosedDialog } from "../components/exhibitor_connect_closed_dialog/exhibitor_connect_closed_dialog";

publicWidget.registry.eventExhibitorConnect = publicWidget.Widget.extend({
    selector: '.o_wesponsor_connect_button',
    /**
     * @override
     * @public
     */
    init: function () {
        this._super(...arguments);
        this._onConnectClick = debounce(this._onConnectClick, 500, true).bind(this);
    },

    /**
     * @override
     * @public
     */
    start: function () {
        var self = this;
        return this._super(...arguments).then(function () {
            self.eventIsOngoing = self.el.dataset.eventIsOngoing || false;
            self.sponsorIsOngoing = self.el.dataset.sponsorIsOngoing || false;
            self.isParticipating = self.el.dataset.isParticipating || false;
            self.userEventManager = self.el.dataset.userEventManager || false;
            self.el.addEventListener("click", self._onConnectClick);
        });
    },

    /**
     * @override
     * @public
     */
    destory () {
        this._super(...arguments);
        this.el.removeEventListener("click", this._onConnectClick);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //-------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     * On click, if sponsor is not within opening hours, display a modal instead
     * of redirecting on the sponsor view;
     */
    _onConnectClick: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();

        if (this.userEventManager) {
            redirect(this.el.dataset.sponsorUrl);
        } else if (!this.eventIsOngoing || ! this.sponsorIsOngoing) {
            return this._openClosedDialog();
        } else {
            redirect(this.el.dataset.sponsorUrl);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _openClosedDialog: function () {
        const sponsorId = parseInt(this.el.dataset.sponsorId);
        this.call("dialog", "add", ExhibitorConnectClosedDialog, { sponsorId });
    },

});


export default {
    eventExhibitorConnect: publicWidget.registry.eventExhibitorConnect,
};
