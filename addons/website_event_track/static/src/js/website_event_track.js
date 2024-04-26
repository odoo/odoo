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
            const popovers = this.el.querySelectorAll('[data-bs-toggle="popover"]');
            popovers.forEach(popover => new bootstrap.Popover(popover));

            const agendas = Array.from(this.el.getElementsByClassName('o_we_online_agenda'));

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
        var text = ev.currentTarget.value;
        var tracks = document.querySelectorAll('.event_track');

        //check if the user is performing a search; i.e., text is not empty
        if (text) {
            function filterTracks(index, element) {
                //when filtering elements only check the text content
                return this.textContent.toLowerCase().includes(text.toLowerCase());
            }
            var filteredTracks = Array.from(tracks).filter(filterTracks);
            document.getElementById('search_summary').classList.remove('invisible');
            document.getElementById('search_number').textContent = filteredTracks.length;

            tracks.forEach(track => track.classList.remove('invisible'));
            Array.from(tracks).filter(track => !filterTracks(null, track)).forEach(track => track.classList.add('invisible'));
        } else {
            //if no search is being performed; hide the result count text
            document.getElementById('search_summary').classList.add('invisible');
            tracks.forEach(track => track.classList.remove('invisible'));
        }
    },
});
