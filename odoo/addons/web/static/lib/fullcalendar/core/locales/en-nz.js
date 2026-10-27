(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory() :
    typeof define === 'function' && define.amd ? define(factory) :
    (global = global || self, (global.FullCalendarLocales = global.FullCalendarLocales || {}, global.FullCalendarLocales['en-nz'] = factory()));
}(this, function () { 'use strict';

    var enNz = {
        code: "en-nz",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        }
    };

    return enNz;

}));
