odoo.define('website_event_booth_exhibitor.booth_sponsor_details', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.boothSponsorDetails = publicWidget.Widget.extend({
    selector: '#contact_details_form',
    events: {
        'click input[id="contact_details"]': '_onClickContactDetails',
    },

    _onClickContactDetails(ev) {
        this.useContactDetails = ev.currentTarget.checked;
        this.$('#o_wevent_contact_details').toggleClass('d-none', !this.useContactDetails);
        this.$('input[name="contact_name"], input[name="contact_email"]').attr('required', this.useContactDetails);
    },

});

    return {
        boothSponsorDetails: publicWidget.registry.boothSponsorDetails,
    };

});
