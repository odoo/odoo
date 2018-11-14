/*global $, _, PDFJS */
odoo.define('website_slides.slides', function (require) {
"use strict";

    var time = require('web.time');
    require('root.widget');

    (function () {
        $("timeago.timeago").each(function (index, el) {
            var datetime = $(el).attr('datetime'),
                datetime_obj = time.str_to_datetime(datetime),
                // if presentation 7 days, 24 hours, 60 min, 60 second, 1000 millis old(one week)
                // then return fix formate string else timeago
                display_str = "";
            if (datetime_obj && new Date().getTime() - datetime_obj.getTime() > 7 * 24 * 60 * 60 * 1000) {
                display_str = moment(datetime_obj).format('ll');
            } else {
                display_str = moment(datetime_obj).fromNow();
            }
            $(el).text(display_str);
        });

        // To prevent showing channel settings alert box once user closed it.
        $('.o_slides_hide_channel_settings').on('click', function(ev) {
            var channel_id = $(this).data("channelId");
            ev.preventDefault();
            document.cookie = "slides_channel_" + channel_id + " = closed";
            return true;
        });
    })();

    return {
        page_widgets: {},
    }
});
