odoo.define('website_slides.course.join.widget', function (require) {
'use strict';

var core = require('web.core');
var publicWidget = require('web.public.widget');
require('website_slides.slides');

var _t = core._t;

var CourseJoinWidget = publicWidget.Widget.extend({
    events: {
        'click .o_wslides_js_course_join_link': '_onClickJoin',
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
        var channelId = $(event.currentTarget).data('channel-id');
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
                    self._popoverAlert(self.$el, _.str.sprintf(_t('Please <a href="/web/login?redirect=%s">login</a> to join this course.'), (document.URL)));
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
    selector: '.o_wslides_wrap',

    /**
     * @override
     * @param {Object} parent
     */
    start: function () {
        var self = this;
        var defs = [this._super.apply(this, arguments)];
        $('.o_wslides_js_course_join').each(function () {
            defs.push(new CourseJoinWidget(self).attachTo($(this)));
        });
        return $.when.apply($, defs);
    },
});


return {
    courseJoinWidget: CourseJoinWidget,
    websiteSlidesCourseJoin: publicWidget.registry.websiteSlidesCourseJoin
};

});
