odoo.define('website_rating_project_issue.rating', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var time = require('web.time');
var base = require('web_editor.base');

base.ready().then(function () {
        if(!$('.oe_website_rating_project').length) {
            return $.Deferred().reject("DOM doesn't contain '.oe_website_rating_project'");
        }

        setTimeout("location.reload(true);", 300000);
        $('.o-rating-image').popover({
            placement: 'top',
            trigger: 'hover',
            html: 'true',
            content: function () {
                var getratingid = $(this).data('id');
                var getratingdate = $(this).data('date');
                var sys_base_rating_time = time.auto_str_to_date(getratingdate);
                var duration = moment(sys_base_rating_time).fromNow();
                $("#rating_"+ getratingid).find(".rating-timeduration").text(duration);
                return $("#rating_"+ getratingid).html();
            }
        });
    });
});
