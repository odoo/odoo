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
        var self = this;
        this.isUser = false;
        const jsFollowEls = this.el.querySelectorAll(".js_follow");

        var always = function (data) {
            self.isUser = data[0].is_user;
            const jsFollowToEnableEls = Array.from(jsFollowEls).filter((el) => {
                const model = el.dataset.object;
                return model in data[1] && data[1][model].includes(parseInt(el.dataset.id));
            });
            self._toggleSubscription(true, data[0].email, jsFollowToEnableEls);
            self._toggleSubscription(
                false,
                data[0].email,
                Array.from(jsFollowEls).filter((el) => !jsFollowToEnableEls.includes(el))
            );
            jsFollowEls.forEach((el) => el.classList.remove("d-none"));
        };

        const records = {};
        jsFollowEls.forEach((el) => {
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
            document
                .querySelectorAll(".js_follow > .d-none")
                .forEach((el) => el.classList.remove("d-none"));
            this.el.querySelectorAll(".js_follow_btn, .js_unfollow_btn").forEach((el) => {
                el.addEventListener("click", (event) => {
                    event.preventDefault();
                    this._onClick(event);
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
    _toggleSubscription(follow, email, jsFollowEls) {
        if (follow) {
            this._updateSubscriptionDOM(follow, email, jsFollowEls);
        } else {
            jsFollowEls.forEach((el) => {
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
    _updateSubscriptionDOM(follow, email, jsFollowEls) {
        jsFollowEls.forEach((el) => {
            const inputEl = el.querySelector(".js_follow_email");
            if (inputEl) {
                inputEl.value = email || "";
                inputEl.disabled = email && (follow || this.isUser);
                el.setAttribute("data-follow", follow ? "on" : "off");
            }
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
        var self = this;
        const jsFollowEl = ev.currentTarget.closest(".js_follow");
        const emailInputEl = jsFollowEl.querySelector(".js_follow_email");

        if (emailInputEl && !emailInputEl.value.match(/.+@.+/)) {
            jsFollowEl.classList.add("o_has_error");
            jsFollowEl
                .querySelectorAll(".form-control, .form-select")
                .forEach((el) => el.classList.add("is-invalid"));
            return false;
        }
        jsFollowEl.classList.remove("o_has_error");
        jsFollowEl
            .querySelectorAll(".form-control, .form-select")
            .forEach((el) => el.classList.remove("is-invalid"));

        const email = emailInputEl ? emailInputEl.value : false;
        if (email || this.isUser) {
            rpc("/website_mail/follow", {
                id: +jsFollowEl.dataset.id,
                object: jsFollowEl.dataset.object,
                message_is_follower: jsFollowEl.getAttribute("data-follow") || "off",
                email: email,
            }).then(function (follow) {
                self._toggleSubscription(follow, email, [jsFollowEl]);
            });
        }
    },
});
