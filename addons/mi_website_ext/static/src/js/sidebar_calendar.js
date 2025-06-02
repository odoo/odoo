/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc"; // Usamos la importación moderna

publicWidget.registry.SidebarCalendar = publicWidget.Widget.extend({
    selector: '#sidebar_calendar_container',

    start: function () {
        return this._super.apply(this, arguments).then(() => {
            if (window.FullCalendar) {
                // ===== CORRECCIÓN: Usamos la llamada directa rpc(ruta, parámetros) =====
                rpc.query({
                    route: "/get_calendar_activities",
                    params: {},
                }).then(events => {
                    this._renderCalendar(events);
                });
            } else {
                console.error("FullCalendar no se ha cargado. Revisa las rutas en el __manifest__.py y actualiza el módulo.");
                this.$el.append($('<p>').text('Error al cargar el calendario.'));
            }
        });
    },

    _renderCalendar(events) {
        const calendarEl = this.el;
        if (!calendarEl) return;

        if (calendarEl.f_calendar) {
            calendarEl.f_calendar.destroy();
        }

        const calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            headerToolbar: {
                left: 'prev',
                center: 'title',
                right: 'next'
            },
            events: events,
            height: 'auto',
            locale: 'es',
            buttonText: { today: 'hoy', month: 'mes' },
            aspectRatio: 1.2,
            dayHeaderFormat: { weekday: 'narrow' },
        });

        calendar.render();
        calendarEl.f_calendar = calendar;
    },
});