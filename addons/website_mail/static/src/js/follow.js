/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.follow = publicWidget.Widget.extend({
    selector: '#wrapwrap:has(.js_follow)',
    disabledInEditableMode: false,

    /**
     * @override
     */
    start: function () {
        let self = this;
        this.isUser = false;
        let jsFollowEls = this.el.querySelectorAll('.js_follow');

        let always = function (data) {
            self.isUser = data[0].is_user;
            const jsFollowToEnable = Array.from(jsFollowEls).filter(function (el) {
                const model = el.dataset.object;
                return model in data[1] && data[1][model].includes(parseInt(el.dataset.id));
            });
            self._toggleSubscription(true, data[0].email, jsFollowToEnable);
            self._toggleSubscription(false, data[0].email, Array.from(jsFollowEls).filter(el => !jsFollowToEnable.includes(el)));
            jsFollowEls.forEach(el => el.classList.remove('d-none'));
        };

        const records = {};
        jsFollowEls.forEach(el => {
            const model = el.dataset.object;
            if (!(model in records)) {
                records[model] = [];
            }
            records[model].push(parseInt(el.dataset.id));
        });

        rpc('/website_mail/is_follower', {
            records: records,
        }).then(always, always);

        // not if editable mode to allow designer to edit
        if (!this.editableMode) {
            document.querySelectorAll('.js_follow > .d-none').forEach(el => el.classList.remove('d-none'));
            this.el.querySelectorAll('.js_follow_btn, .js_unfollow_btn').forEach(el => {
                el.addEventListener('click', function (event) {
                    event.preventDefault();
                    self._onClick(event);
                });
            });
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Toggles subscription state for every given records.
     *
     * @private
     * @param {boolean} follow
     * @param {string} email
     * @param {Array} jsFollowEls
     */
    _toggleSubscription: function (follow, email, jsFollowEls) {
        if (follow) {
            this._updateSubscriptionDOM(follow, email, jsFollowEls);
        } else {
            jsFollowEls.forEach(el => {
                const follow = !email && el.getAttribute('data-unsubscribe');
                this._updateSubscriptionDOM(follow, email, [el]);
            });
        }
    },
    /**
     * Updates subscription DOM for every given records.
     * This should not be called directly, use `_toggleSubscription`.
     *
     * @private
     * @param {boolean} follow
     * @param {string} email
     * @param {Array} jsFollowEls
     */
    _updateSubscriptionDOM: function (follow, email, jsFollowEls) {
        jsFollowEls.forEach(el => {
            let input = el.querySelector('input.js_follow_email');
            input.value = email || "";
            input.disabled = email && (follow || this.isUser);
            el.setAttribute("data-follow", follow ? 'on' : 'off');
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onClick: function (ev) {
        let self = this;
        let jsFollow = ev.currentTarget.closest('.js_follow');
        let emailInput = jsFollow.querySelector(".js_follow_email");

        if (emailInput && !emailInput.value.match(/.+@.+/)) {
            jsFollow.classList.add('o_has_error');
            jsFollow.querySelectorAll('.form-control, .form-select').forEach(el => el.classList.add('is-invalid'));
            return false;
        }
        jsFollow.classList.remove('o_has_error');
        jsFollow.querySelectorAll('.form-control, .form-select').forEach(el => el.classList.remove('is-invalid'));

        let email = emailInput ? emailInput.value : false;
        if (email || this.isUser) {
            rpc('/website_mail/follow', {
                'id': +jsFollow.dataset.id,
                'object': jsFollow.dataset.object,
                'message_is_follower': jsFollow.getAttribute("data-follow") || "off",
                'email': email,
            }).then(function (follow) {
                self._toggleSubscription(follow, email, [jsFollow]);
            });
        }
    },
});
