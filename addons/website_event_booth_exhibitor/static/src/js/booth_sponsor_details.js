import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.boothSponsorDetails = publicWidget.Widget.extend({
    selector: '#o_wbooth_contact_details_form',
    events: {
        'click input[id="contact_details"]': '_onClickContactDetails',
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    _onClickContactDetails(ev) {
        this.useContactDetails = ev.currentTarget.checked;
        this.el
            .querySelector("#o_wbooth_contact_details")
            .classList.toggle("d-none", !this.useContactDetails);
        this.el
            .querySelectorAll(
                "label[for='sponsor_name'] > .mandatory_mark, label[for='sponsor_email'] > .mandatory_mark"
            )
            .forEach((el) => {
                el.classList.toggle("d-none", this.useContactDetails);
            });
        this.el
            .querySelectorAll("input[name='contact_name'], input[name='contact_email']")
            .forEach((inputEl) => (inputEl.required = this.useContactDetails));
    },

});

export default {
    boothSponsorDetails: publicWidget.registry.boothSponsorDetails,
};
