// moment.js locale configuration
// locale : afrikaans (af)
// author : Werner Mollentze : https://github.com/wernerm

(function (factory) {
    if (typeof define === 'function' && define.amd) {
        define(['moment'], factory); // AMD
    } else if (typeof exports === 'object') {
        module.exports = factory(require('../moment')); // Node
    } else {
        factory(window.moment); // Browser global
    }
}(function (moment) {
    return moment.defineLocale('af', {
        months : "Januarie_Februarie_Maart_April_Mei_Junie_Julie_Augustus_September_Oktober_November_Desember".split("_"),
        monthsShort : "Jan_Feb_Mar_Apr_Mei_Jun_Jul_Aug_Sep_Okt_Nov_Des".split("_"),
        weekdays : "Sondag_Maandag_Dinsdag_Woensdag_Donderdag_Vrydag_Saterdag".split("_"),
        weekdaysShort : "Son_Maa_Din_Woe_Don_Vry_Sat".split("_"),
        weekdaysMin : "So_Ma_Di_Wo_Do_Vr_Sa".split("_"),
        meridiem : function (hours, minutes, isLower) {
            if (hours < 12) {
                return isLower ? 'vm' : 'VM';
            } else {
                return isLower ? 'nm' : 'NM';
            }
        },
        longDateFormat : {
            LT : "HH:mm",
            L : "DD/MM/YYYY",
            LL : "D MMMM YYYY",
            LLL : "D MMMM YYYY LT",
            LLLL : "dddd, D MMMM YYYY LT"
        },
        calendar : {
            sameDay : '[Vandag om] LT',
            nextDay : '[Môre om] LT',
            nextWeek : 'dddd [om] LT',
            lastDay : '[Gister om] LT',
            lastWeek : '[Laas] dddd [om] LT',
            sameElse : 'L'
        },
        relativeTime : {
            future : "oor %s",
            past : "%s gelede",
            s : "'n paar sekondes",
            m : "'n minuut",
            mm : "%d minute",
            h : "'n uur",
            hh : "%d ure",
            d : "'n dag",
            dd : "%d dae",
            M : "'n maand",
            MM : "%d maande",
            y : "'n jaar",
            yy : "%d jaar"
        },
        ordinal : function (number) {
            return number + ((number === 1 || number === 8 || number >= 20) ? 'ste' : 'de'); // Thanks to Joris Röling : https://github.com/jjupiter
        },
        week : {
            dow : 1, // Maandag is die eerste dag van die week.
            doy : 4  // Die week wat die 4de Januarie bevat is die eerste week van die jaar.
        }
    });
}));
