odoo.define('website_event_track.website_event_track', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.websiteEventTrack = publicWidget.Widget.extend({
    selector: '.o_wevent_event',
    events: {
        'input #event_track_search': '_onEventTrackSearchInput',
    },

    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments).then(() => {

            let current = null;
            let focus = false;
            let timer = null;

            let onEnter = () => { focus = true; };
            let onLeave = () => {
                if (focus) {
                    hide();
                    focus = false;
                    clearTimeout(timer);
                }
            };

            let show = () => {
                if (current) {
                    $(current).popover('show');
                    const $popover = $('#' + current.getAttribute('aria-describedby'));
                    $popover.on('mouseenter', onEnter);
                    $popover.on('mouseleave', onLeave);
                }
            };

            let hide = () => {
                if (current) {
                    const $popover = $('#' + current.getAttribute('aria-describedby'));
                    $popover.off('mouseenter', onEnter);
                    $popover.off('mouseleave', onLeave);
                    $(current).popover('hide');
                    let hover = $('[data-toggle="popover"]:hover');
                    if (hover.length === 0) {
                        current = null;
                    } else {
                        current = hover.get(0);
                        show();
                    }
                }
            };

            this.$el.find('[data-toggle="popover"]').popover({
                trigger: 'manual'
            }).on('mouseenter', function () {
                if (!current) {
                    current = this;
                    show();
                }
            }).on('mouseleave', function () {
                if (current === this) {
                    timer = setTimeout(() => {
                        if (!focus) { hide(); }
                    }, 200);
                }
            });
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onEventTrackSearchInput: function (ev) {
        ev.preventDefault();
        var text = $(ev.currentTarget).val();
        var $tracks = $('.event_track');

        //check if the user is performing a search; i.e., text is not empty
        if (text) {
            function filterTracks(index, element) {
                //when filtering elements only check the text content
                return this.textContent.toLowerCase().includes(text.toLowerCase());
            }
            $('#search_summary').removeClass('invisible');
            $('#search_number').text($tracks.filter(filterTracks).length);

            $tracks.removeClass('invisible').not(filterTracks).addClass('invisible');
        } else {
            //if no search is being performed; hide the result count text
            $('#search_summary').addClass('invisible');
            $tracks.removeClass('invisible')
        }
    },
});
});
