odoo.define('website_rating_project.rating', function (require) {
'use strict';

var time = require('web.time');
var publicWidget = require('web.public.widget');

publicWidget.registry.ProjectRatingImage = publicWidget.Widget.extend({
    selector: '.o_portal_project_rating .o_rating_image',

    /**
     * @override
     */
    start: function () {
        this.$el.popover({
            placement: 'bottom',
            trigger: 'hover',
            html: true,
            content: function () {
                var $elem = $(this);
                var id = $elem.data('id');
                var ratingDate = $elem.data('rating-date');
                var baseDate = time.auto_str_to_date(ratingDate);
                var duration = moment(baseDate).fromNow();
                var $rating = $('#rating_' + id);
                $rating.find('.rating_timeduration').text(duration);
                return $rating.html();
            },
        });
        return this._super.apply(this, arguments);
    },
});
});
