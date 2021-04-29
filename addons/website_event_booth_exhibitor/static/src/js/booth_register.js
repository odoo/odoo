odoo.define('website_event_booth_exhibitor.booth_registration', function (require) {
'use strict';

const BoothRegistration = require('website_event_booth.booth_registration');
const core = require('web.core');
const session = require('web.session');

const _t = core._t;

BoothRegistration.include({

    _onChangeBoothType(ev) {
        this.categoryUseSponsor = $(ev.currentTarget).data('use-sponsor');
        return this._super.apply(this, arguments);
    },

    _updateUiAfterBoothCategoryChange() {
        this._super.apply(this, arguments);
        this._updateSubmitButton();
    },

    _updateSubmitButton() {
        let btnText = _t('Book My Booth');
        if (this.categoryUseSponsor) {
            btnText = _t('Fill Sponsor Details');
        }
        else if (session.is_website_user) {
            btnText = _t('Continue');
        }
        let $button = this.$('button.booth-submit');
        $button.text(btnText);
    },

});

});
