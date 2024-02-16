/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.websiteEventTrackML = publicWidget.Widget.extend({
    selector: '.o_wevent_event',

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments).then(() => {
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
            agendaEl.classList.toggle(
                'o_we_online_agenda_has_scroll',
                agendaEl.querySelector('table').clientWidth > agendaEl.clientWidth
            );
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
        agendaEl.classList.toggle('o_we_online_agenda_has_scroll', gap > Math.ceil(agendaEl.scrollLeft));

        requestAnimationFrame(() => {
            setTimeout(() => {
                agendaEl.classList.remove('o_we_online_agenda_is_scrolling');
            }, 200);
        });
    },
});
