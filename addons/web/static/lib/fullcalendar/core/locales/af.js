(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory() :
    typeof define === 'function' && define.amd ? define(factory) :
    (global = global || self, (global.FullCalendarLocales = global.FullCalendarLocales || {}, global.FullCalendarLocales.af = factory()));
}(this, function () { 'use strict';

    var af = {
        code: "af",
        week: {
            dow: 1,
            doy: 4 // Die week wat die 4de Januarie bevat is die eerste week van die jaar.
        },
        buttonText: {
            prev: "Vorige",
            next: "Volgende",
            today: "Vandag",
            year: "Jaar",
            month: "Maand",
            week: "Week",
            day: "Dag",
            list: "Agenda"
        },
        allDayHtml: "Heeldag",
        eventLimitText: "Addisionele",
        noEventsMessage: "Daar is geen gebeurtenisse nie"
    };

    return af;

}));
