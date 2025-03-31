/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { SlideUnsubscribeDialog } from "./public/components/slide_unsubscribe_dialog/slide_unsubscribe_dialog";

publicWidget.registry.websiteSlidesUnsubscribe = publicWidget.Widget.extend({
    selector: '.o_wslides_js_channel_unsubscribe',
    events: {
        'click': '_onUnsubscribeClick',
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _openDialog: function ($element) {
        var data = $element.data();
        this.call("dialog", "add", SlideUnsubscribeDialog, data);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onUnsubscribeClick: function (ev) {
        ev.preventDefault();
        this._openDialog($(ev.currentTarget));
    },
});

export default {
    websiteSlidesUnsubscribe: publicWidget.registry.websiteSlidesUnsubscribe
};
