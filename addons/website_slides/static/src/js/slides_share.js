odoo.define('website_slides.slides_share', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
require('website_slides.slides');

var ShareMail = publicWidget.Widget.extend({
    events: {
        'click button': '_sendMail',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _sendMail: function () {
        var self = this;
        var input = this.$('input');
        var slideID = this.$('button').data('slide-id');
        if (input.val() && input[0].checkValidity()) {
            this.$el.removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');
            this._rpc({
                route: '/slides/slide/send_share_email',
                params: {
                    slide_id: slideID,
                    email: input.val(),
                },
            }).then(function () {
                self.$el.html($('<div class="alert alert-info" role="alert"><strong>Thank you!</strong> Mail has been sent.</div>'));
            });
        } else {
            this.$el.addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
            input.focus();
        }
    },
});

publicWidget.registry.websiteSlidesShare = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    events: {
        'click a.o_slides_social_share': '_onSlidesSocialShare',
    },

    /**
     * @override
     * @param {Object} parent
     */
    start: function (parent) {
        var defs = [this._super.apply(this, arguments)];
        defs.push(new ShareMail(this).attachTo($('.oe_slide_js_share_email')));

        return Promise.all(defs);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {Object} ev
     */
    _onSlidesSocialShare: function (ev) {
        ev.preventDefault();
        var popUpURL = $(ev.currentTarget).attr('href');
        var popUp = window.open(popUpURL, 'Share Dialog', 'width=626,height=436');
        $(window).on('focus', function () {
            if (popUp.closed) {
                $(window).off('focus');
            }
        });
    },
});
});
