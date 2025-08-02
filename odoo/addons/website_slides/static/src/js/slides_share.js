/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import '@website_slides/js/slides';
import { _t } from "@web/core/l10n/translation";
import { browser } from '@web/core/browser/browser';

export const ShareMail = publicWidget.Widget.extend({
    events: {
        'click button': '_sendMail',
        'keypress input': '_onKeypress',
    },

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
        this.notification = this.bindService("notification");
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Send the email(s) on 'Enter' key
     *
     * @private
     * @param {Event} ev
     */
    _onKeypress: function (ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this._sendMail();
        }
    },

    /**
     * @private
     */
    _sendMail: function () {
        const input = this.$('input');
        if (input.val()) {
            const slideID = this.$('button').data('slide-id');
            const channelID = this.$('button').data('channel-id');
            const params = {
                emails: input.val(),
            };
            let route;
            if (slideID) {
                route = '/slides/slide/send_share_email';
                params.slide_id = slideID;
            } else if (channelID) {
                route = '/slides/channel/send_share_email';
                params.channel_id = channelID;
            }
            this.$el.removeClass('o_has_error').find('.form-control, .form-select').removeClass('is-invalid');
            this.rpc(route, params).then((action) => {
                if (action) {
                    this.$('.alert-info').removeClass('d-none');
                    this.$('.input-group').addClass('d-none');
                } else {
                    this.notification.add(_t('Please enter valid email(s)'), { type: 'danger' });
                    this.$el.addClass('o_has_error').find('.form-control, .form-select').addClass('is-invalid');
                    input.focus();
                }
            });
        } else {
            this.notification.add(_t('Please enter valid email(s)'), { type: 'danger' });
            this.$el.addClass('o_has_error').find('.form-control, .form-select').addClass('is-invalid');
            input.focus();
        }
    },
});

publicWidget.registry.websiteSlidesShare = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    events: {
        'click a.o_wslides_js_social_share': '_onSlidesSocialShare',
        'click .o_clipboard_button': '_onShareLinkCopy',
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
        ev.stopPropagation();
        var popUpURL = $(ev.currentTarget).attr('href');
        var popUp = window.open(popUpURL, 'Share Dialog', 'width=626,height=436');
        $(window).on('focus', function () {
            if (popUp.closed) {
                $(window).off('focus');
            }
        });
    },

    _onShareLinkCopy: async function (ev) {
        ev.preventDefault();
        var $clipboardBtn = $(ev.currentTarget);
        $clipboardBtn.tooltip({title: "Copied!", trigger: "manual", placement: "bottom"});
        var share_link_el = this.$('#wslides_share_link_id_' + $clipboardBtn[0].id.split('id_')[1]);
        await browser.navigator.clipboard.writeText(share_link_el.val() || '');
        $clipboardBtn.tooltip('show');
        setTimeout(() => $clipboardBtn.tooltip("hide"), 800);
    },
});

publicWidget.registry.websiteSlidesEmbedShare = publicWidget.Widget.extend({
    selector: '.oe_slide_js_embed_code_widget',
    events: {
        'click .o_embed_clipboard_button': '_onShareLinkCopy',
    },

    _onShareLinkCopy: async function (ev) {
        ev.preventDefault();
        const $clipboardBtn = $(ev.currentTarget);
        $clipboardBtn.tooltip({title: "Copied!", trigger: "manual", placement: "bottom"});
        var share_embed_el = this.$('#wslides_share_embed_id_' + $clipboardBtn[0].id.split('id_')[1]);
        await browser.navigator.clipboard.writeText(share_embed_el.val() || '');
        $clipboardBtn.tooltip('show');
        setTimeout(function () {
            $clipboardBtn.tooltip("hide");
        }, 800);
    },
});

export const WebsiteSlidesShare = publicWidget.registry.websiteSlidesShare;
export const WebsiteSlidesEmbedShare = publicWidget.registry.websiteSlidesEmbedShare;
