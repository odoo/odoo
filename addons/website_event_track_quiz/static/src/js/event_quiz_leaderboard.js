/** @odoo-module alias=website_event_track_quiz.event_leaderboard **/


import publicWidget from "web.public.widget";

publicWidget.registry.EventLeaderboard = publicWidget.Widget.extend({
    selector: '.o_wevent_quiz_leaderboard',

    /**
     * Basic override to scroll to current visitor's position.
     */
    start: function () {
        var self = this;
        return this._super(...arguments).then(function () {
            var $scrollTo = self.$('.o_wevent_quiz_scroll_to');
            if ($scrollTo.length !== 0) {
                var offset = $('.o_header_standard').height();
                var $appMenu = $('.o_main_navbar');
                if ($appMenu.length !== 0) {
                    offset += $appMenu.height();
                }
                window.scrollTo({
                    top: $scrollTo.offset().top - offset,
                    behavior: 'smooth'
                });
            }
        });
    }
});

export default publicWidget.registry.EventLeaderboard;
