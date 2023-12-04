/** @odoo-module **/

import { sprintf } from '@web/core/utils/strings';
import { renderToElement } from "@web/core/utils/render";
import publicWidget from '@web/legacy/js/public/public_widget';
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

var CourseJoinWidget = publicWidget.Widget.extend({
    template: 'slide.course.join',
    events: {
        'click .o_wslides_js_course_join_link': '_onClickJoin',
    },

    /**
     *
     * Overridden to add options parameters.
     *
     * @param {Object} parent
     * @param {Object} options
     * @param {Object} options.channel slide.channel information
     * @param {boolean} options.isMember whether current user is enrolled
     * @param {boolean} options.isMemberOrInvited whether current user is at least invited
     * @param {string} options.inviteHash hash of the invited attendee. Needed to grant
     *   access to a course preview / to identify.
     * @param {integer} options.invitePartnerId id of partner of invited attendee if any.
     *   Also needed to access course preview / to identify.
     * @param {boolean} options.invitePreview whether the course is rendered as a preview.
     *   This is true when an invited attendee is on the course while unlogged.
     * @param {boolean} options.isPartnerWithoutUser whether invited partner has users. Used
     *   to redirect properly to sign up / log in.
     * @param {string} [options.joinMessage] the message to use for the simple join case
     *   when the course is free and the user is logged in, defaults to "Join this Course".
     * @param {Promise} [options.beforeJoin] a promise to execute before we redirect to
     *   another url within the join process (login / buy course / ...)
     * @param {function} [options.afterJoin] a callback function called after the user has
     *   joined the course
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.channel = options.channel;
        this.isMember = options.isMember;
        this.isMemberOrInvited = options.isMemberOrInvited;
        this.inviteHash = options.inviteHash;
        this.invitePartnerId = options.invitePartnerId;
        this.invitePreview = options.invitePreview;
        this.isPartnerWithoutUser = options.isPartnerWithoutUser;
        this.publicUser = options.publicUser;
        this.joinMessage = options.joinMessage || _t('Join this Course');
        this.beforeJoin = options.beforeJoin || function () {return Promise.resolve();};
        this.afterJoin = options.afterJoin || function () {document.location.reload();};
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickJoin: function (ev) {
        ev.preventDefault();

        if (this.invitePreview || (this.channel.channelEnroll === 'invite' && this.isMemberOrInvited)) {
            this.joinChannel(this.channel.channelId);
            return;
        }

        if (this.channel.channelEnroll !== 'invite') {
            if (this.publicUser) {
                this.beforeJoin().then(this._redirectToLogin.bind(this));
            } else if (!this.isMember) {
                this.joinChannel(this.channel.channelId);
            }
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Builds a login page that then redirects to this slide page, or the channel if the course
     * is not configured as public enroll type.
     *
     * @private
     */
    _redirectToLogin: function () {
        var url;
        if (this.channel.channelEnroll === 'public') {
            url = window.location.pathname;
            if (document.location.href.indexOf("fullscreen") !== -1) {
                url += '?fullscreen=1';
            }
        } else {
            url = `/slides/${encodeURIComponent(this.channel.channelId)}`;
        }
        document.location = sprintf('/web/login?redirect=%s', encodeURIComponent(url));
    },

    /**
     * @private
     * @param {Object} $el
     * @param {String} message
     */
    _popoverAlert: function ($el, message) {
        $el.popover({
            trigger: 'focus',
            delay: {'hide': 300},
            placement: 'bottom',
            container: 'body',
            html: true,
            content: function () {
                return message;
            }
        }).popover('show');
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /**
     * @public
     * @param {integer} channelId
     */
    joinChannel: function (channelId) {
        var self = this;
        rpc('/slides/channel/join', {
            channel_id: channelId,
        }).then(function (data) {
            if (!data.error) {
                self.afterJoin();
            } else {
                if (data.error === 'public_user') {
                    const popupContent = renderToElement('slide.course.join.popupContent', {
                        channelId: channelId,
                        courseUrl: encodeURIComponent(document.URL),
                        errorSignupAllowed: data.error_signup_allowed,
                        widget: self,
                    });
                    self._popoverAlert(self.$el, popupContent);
                } else if (data.error === 'join_done') {
                    self._popoverAlert(self.$el, _t('You have already joined this channel'));
                } else {
                    self._popoverAlert(self.$el, _t('Unknown error'));
                }
            }
        });
    },
});

publicWidget.registry.websiteSlidesCourseJoin = publicWidget.Widget.extend({
    selector: '.o_wslides_js_course_join_link',

    /**
     * @override
     * @param {Object} parent
     */
    start: function () {
        var self = this;
        var proms = [this._super.apply(this, arguments)];
        var data = self.$el.data();
        var options = {
            channel: {
                channelEnroll: data.channelEnroll,
                channelId: data.channelId
            },
            inviteHash: data.inviteHash,
            invitePartnerId: data.invitePartnerId,
            invitePreview: data.invitePreview,
            isMemberOrInvited: data.isMemberOrInvited,
            isPartnerWithoutUser: data.isPartnerWithoutUser
        };
        $('.o_wslides_js_course_join').each(function () {
            proms.push(new CourseJoinWidget(self, options).attachTo($(this)));
        });
        return Promise.all(proms);
    },
});

export default {
    courseJoinWidget: CourseJoinWidget,
    websiteSlidesCourseJoin: publicWidget.registry.websiteSlidesCourseJoin
};
