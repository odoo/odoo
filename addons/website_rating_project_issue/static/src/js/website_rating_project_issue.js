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
            placement: 'bottom',
            trigger: 'hover',
            html: 'true',
            content: function () {
                var id = $(this).data('id');
                var rating_date = $(this).data('rating-date');
                var base_date = time.auto_str_to_date(rating_date);
                var duration = moment(base_date).fromNow();
                $("#rating_"+ id).find(".rating-timeduration").text(duration);
                return $("#rating_"+ id).html();
            }
        });
    });
});
