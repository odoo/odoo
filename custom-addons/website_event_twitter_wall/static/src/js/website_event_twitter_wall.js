/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * The default behavior of the Twitter Wall is to 'zoom' the browser.
 * (See base _zoom method for details)
 *
 * As we don't want that zoom behavior when embedding the wall in the event,
 * we zoom to 0 then disable the function entirely.
 */
publicWidget.registry.websiteTwitterWall.include({
    start: function () {
        this._super(...arguments);

        if (this.$el.closest('.o_wevent_event').length !== 0) {
            // force zoom to '1' on our event page
            this.twitterWall._zoom(1);
        }
    },

    /**
     * Override of the base method that will also re-organize tweets displayed on the page
     * based on the selected number of columns.
     * e.g: If you are on a single column and you add a second one, the method
     * will split existing tweets on the single columns to split them on both resulting columns.
     *
     * @param {Integer} columnCount Number of columns to display
     * @param {Boolean} singleTweetView Show a single tweet row (only on full screen view)
     */
    _setColumns: function (columnCount, singleTweetView) {
        $('.o-tw-walls-col').addClass('o-tw-walls-col-remove');

        var tweetsCount = $('.o-tw-tweet').length;
        var newColumns = [];
        var slicedTweets = [];
        for (var i = 0; i < columnCount; i++) {
            var $newColumn = $('<div>', {
                class: 'o-tw-walls-col col-md-' + (12 / columnCount)
            });
            $newColumn.appendTo($('.o-tw-walls'));
            newColumns.push($newColumn);

            var start = Math.floor(i * (tweetsCount / columnCount));
            var end = undefined;
            if (i !== columnCount - 1) {
                end = Math.floor((i + 1) * (tweetsCount / columnCount));
            }
            slicedTweets.push($('.o-tw-tweet').slice(start, end));
        }

        newColumns.forEach(function (column, index) {
            slicedTweets[index].appendTo(column);
        });

        $('.o-tw-walls-col.o-tw-walls-col-remove').remove();

        if (singleTweetView) {
            $('.o-tw-walls-col').addClass('o-tw-tweet-single');
        } else if (singleTweetView === false) {
            $('.o-tw-walls-col').removeClass('o-tw-tweet-single');
        }
        if (newColumns.length > 0) {
            this.twitterWall.prependTweetsTo = newColumns[0];
        }
    }
});
