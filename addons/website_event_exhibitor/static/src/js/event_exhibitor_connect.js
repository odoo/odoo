/** @odoo-module **/

import { debounce } from "@web/core/utils/timing";
import publicWidget from "@web/legacy/js/public/public_widget";
import { ExhibitorConnectClosedDialog } from "../components/exhibitor_connect_closed_dialog/exhibitor_connect_closed_dialog";

publicWidget.registry.eventExhibitorConnect = publicWidget.Widget.extend({
    selector: '.o_wesponsor_connect_button',
    /**
     * @override
     * @public
     */
    init: function () {
        this._super(...arguments);
        this._onConnectClick = debounce(this._onConnectClick, 500, true);
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
            self.el.addEventListener('click', self._onConnectClick.bind(self));
        });
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
            document.location = this.el.dataset.sponsorUrl;
        } else if (!this.eventIsOngoing && !this.isParticipating) {
            document.location = this.el.dataset.registerUrl;
        } else if (!this.eventIsOngoing || ! this.sponsorIsOngoing) {
            return this._openClosedDialog();
        } else {
            document.location = this.el.dataset.sponsorUrl;
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _openClosedDialog: function (element) {
        const sponsorId = this.el.dataset.sponsorId;
        this.call("dialog", "add", ExhibitorConnectClosedDialog, { sponsorId });
    },

});


export default {
    eventExhibitorConnect: publicWidget.registry.eventExhibitorConnect,
};
