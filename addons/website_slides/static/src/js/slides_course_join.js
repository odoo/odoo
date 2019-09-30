odoo.define('website_slides.course.join.widget', function (require) {
'use strict';

var core = require('web.core');
var publicWidget = require('web.public.widget');

var _t = core._t;

var CourseJoinWidget = publicWidget.Widget.extend({
    template: 'slide.course.join',
    xmlDependencies: ['/website_slides/static/src/xml/channel_management.xml'],
    events: {
        'click .o_wslides_js_course_join_link': '_onClickJoin',
    },
    
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.channel = options.channel;
        this.isMember = options.isMember;
        this.publicUser = options.publicUser;
        this.beforeJoin = options.beforeJoin;
        this.afterJoin = options.afterJoin || function () {location.reload();};
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
        if (this.channel.channelEnroll === 'public') {
            if (this.publicUser) {
                this._signInAndJoinCourse();
            } else if (!this.isMember) {
                this.joinChannel(this.channel.channelId);
            }
        }
    },
    
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * @private
     */
    _createLoginRedirectUrl: function (url) {
        var baseUrl = url || window.location.pathname;
        var params = {};
        if (window.location.href.indexOf("fullscreen") > -1) {
            params.fullscreen = 1;
        }
        baseUrl = _.str.sprintf('%s?%s', baseUrl, $.param(params));
        return _.str.sprintf('/web/login?redirect=%s', encodeURIComponent(baseUrl));
    },

    /**
     * @private
     * @param {Object} $el
     * @param {String} message
     */
    _popoverAlert: function ($el, message) {
        $el.popover({
            trigger: 'focus',
            placement: 'bottom',
            container: 'body',
            html: true,
            content: function () {
                return message;
            }
        }).popover('show');
    },
    /**
     * @private
     */
    _signInAndJoinCourse: function () {
        if (this.channel.channelEnroll === 'public') {
            var self = this;
            this.beforeJoin().then(function () {
                window.location.href = self._createLoginRedirectUrl(); 
            });
        }
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
                    var message = _t('Please <a href="/web/login?redirect=%s">login</a> to join this course');
                    var signupAllowed = data.error_signup_allowed || false;
                    if (signupAllowed) {
                        message = _t('Please <a href="/web/signup?redirect=%s">create an account</a> to join this course');
                    }
                    self._popoverAlert(self.$el, _.str.sprintf(message, (document.URL)));
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

return {
    courseJoinWidget: CourseJoinWidget,
    websiteSlidesCourseJoin: publicWidget.registry.websiteSlidesCourseJoin
};

});
