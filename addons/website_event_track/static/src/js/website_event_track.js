/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.websiteEventTrack = publicWidget.Widget.extend({
    selector: '.o_wevent_event',
    events: {
        'input #event_track_search': '_onEventTrackSearchInput',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments).then(() => {
            this.$el.find('[data-bs-toggle="popover"]').popover();

            const agendas = Array.from(this.target.getElementsByClassName('o_we_online_agenda'));

            if (agendas.length > 0) {
                this._checkAgendasOverflow(agendas);

                agendas.forEach(agenda => {
                    agenda.addEventListener('scroll', event => {
                        this._onAgendaScroll(agenda, event);
                    });
                });

                window.addEventListener('resize', () => {
                    this._checkAgendasOverflow(agendas);
                });
            }
        })
    },

    /**
     * @private
     * @param {Object} agendas
     */
    _checkAgendasOverflow: function (agendas) {
        agendas.forEach(agendaEl => {
            const hasScroll = agendaEl.querySelector('table').clientWidth > agendaEl.clientWidth;

            agendaEl.classList.toggle('o_we_online_agenda_has_scroll', hasScroll);
            agendaEl.classList.toggle('o_we_online_agenda_has_content_hidden', hasScroll);
        });
    },

    /**
     * @private
     * @param {Object} agendaEl
     * @param {Event} event
     */
    _onAgendaScroll: function (agendaEl, event) {
        const tableEl = agendaEl.querySelector('table');
        const gutter = 15; // = half $grid-gutter-width
        const gap = tableEl.clientWidth - agendaEl.clientWidth - gutter;

        agendaEl.classList.add('o_we_online_agenda_is_scrolling');
        agendaEl.classList.toggle('o_we_online_agenda_has_content_hidden', gap > Math.ceil(agendaEl.scrollLeft));

        requestAnimationFrame(() => {
            setTimeout(() => {
                agendaEl.classList.remove('o_we_online_agenda_is_scrolling');
            }, 200);
        });
    },

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
