odoo.define('website_slides.course.join.widget', function (require) {
'use strict';

var core = require('web.core');
var publicWidget = require('web.public.widget');
require('website_slides.slides');

var _t = core._t;

var CourseJoinWidget = publicWidget.Widget.extend({
    template: 'slide.course.join',
    xmlDependencies: ['/website_slides/static/src/xml/channel_management.xml'],
    events: {
        'click .o_wslides_js_course_join_link': '_onClickJoin',
    },

    init: function (parent, channelId){
        this.channelId = channelId;
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickJoin: function (event) {
        var channelId = this.channelId || $(event.currentTarget).data('channel-id');
        var self = this;
        this._rpc({
            route: '/slides/channel/join',
            params: {
                channel_id: channelId,
            },
        }).then(function (data) {
            if (! data.error) {
                location.reload();
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
        $('.o_wslides_js_course_join').each(function () {
            proms.push(new CourseJoinWidget(self).attachTo($(this)));
        });
        return Promise.all(proms);
    },
});


return {
    courseJoinWidget: CourseJoinWidget,
    websiteSlidesCourseJoin: publicWidget.registry.websiteSlidesCourseJoin
};

});
