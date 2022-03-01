/** @odoo-module **/

import { sprintf } from '@web/core/utils/strings';
import { _t } from 'web.core';
import publicWidget from 'web.public.widget';

var CourseJoinWidget = publicWidget.Widget.extend({
    template: 'slide.course.join',
    xmlDependencies: ['/website_slides/static/src/xml/slide_course_join.xml'],
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
     * @param {boolean} options.isMember whether current user is member or not
     * @param {boolean} options.publicUser whether current user is public or not
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

        if (this.channel.channelEnroll !== 'invite') {
            if (this.publicUser) {
                this.beforeJoin().then(this._redirectToLogin.bind(this));
            } else if (!this.isMember && this.channel.channelEnroll === 'public') {
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
            url = `/slides/${this.channel.channelId}`;
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
        this._rpc({
            route: '/slides/channel/join',
            params: {
                channel_id: channelId,
            },
        }).then(function (data) {
            if (!data.error) {
                self.afterJoin();
            } else {
                if (data.error === 'public_user') {
                    const message = data.error_signup_allowed ?
                        _t('Please <a href="/web/login?redirect=%s">login</a> or <a href="/web/signup?redirect=%s">create an account</a> to join this course') :
                        _t('Please <a href="/web/login?redirect=%s">login</a> to join this course');
                    self._popoverAlert(self.$el, sprintf(message, document.URL, document.URL));
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
        var options = {channel: {channelEnroll: data.channelEnroll, channelId: data.channelId}};
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
