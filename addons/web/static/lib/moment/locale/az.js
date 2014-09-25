// moment.js locale configuration
// locale : azerbaijani (az)
// author : topchiyev : https://github.com/topchiyev

(function (factory) {
    if (typeof define === 'function' && define.amd) {
        define(['moment'], factory); // AMD
    } else if (typeof exports === 'object') {
        module.exports = factory(require('../moment')); // Node
    } else {
        factory(window.moment); // Browser global
    }
}(function (moment) {
    var suffixes = {
        1: "-inci",
        5: "-inci",
        8: "-inci",
        70: "-inci",
        80: "-inci",

        2: "-nci",
        7: "-nci",
        20: "-nci",
        50: "-nci",

        3: "-üncü",
        4: "-üncü",
        100: "-üncü",

        6: "-ncı",

        9: "-uncu",
        10: "-uncu",
        30: "-uncu",

        60: "-ıncı",
        90: "-ıncı"
    };
    return moment.defineLocale('az', {
        months : "yanvar_fevral_mart_aprel_may_iyun_iyul_avqust_sentyabr_oktyabr_noyabr_dekabr".split("_"),
        monthsShort : "yan_fev_mar_apr_may_iyn_iyl_avq_sen_okt_noy_dek".split("_"),
        weekdays : "Bazar_Bazar ertəsi_Çərşənbə axşamı_Çərşənbə_Cümə axşamı_Cümə_Şənbə".split("_"),
        weekdaysShort : "Baz_BzE_ÇAx_Çər_CAx_Cüm_Şən".split("_"),
        weekdaysMin : "Bz_BE_ÇA_Çə_CA_Cü_Şə".split("_"),
        longDateFormat : {
            LT : "HH:mm",
            L : "DD.MM.YYYY",
            LL : "D MMMM YYYY",
            LLL : "D MMMM YYYY LT",
            LLLL : "dddd, D MMMM YYYY LT"
        },
        calendar : {
            sameDay : '[bugün saat] LT',
            nextDay : '[sabah saat] LT',
            nextWeek : '[gələn həftə] dddd [saat] LT',
            lastDay : '[dünən] LT',
            lastWeek : '[keçən həftə] dddd [saat] LT',
            sameElse : 'L'
        },
        relativeTime : {
            future : "%s sonra",
            past : "%s əvvəl",
            s : "birneçə saniyyə",
            m : "bir dəqiqə",
            mm : "%d dəqiqə",
            h : "bir saat",
            hh : "%d saat",
            d : "bir gün",
            dd : "%d gün",
            M : "bir ay",
            MM : "%d ay",
            y : "bir il",
            yy : "%d il"
        },
        meridiem : function (hour, minute, isLower) {
            if (hour < 4) {
                return "gecə";
            } else if (hour < 12) {
                return "səhər";
            } else if (hour < 17) {
                return "gündüz";
            } else {
                return "axşam";
            }
        },
        ordinal : function (number) {
            if (number === 0) {  // special case for zero
                return number + "-ıncı";
            }
            var a = number % 10,
                b = number % 100 - a,
                c = number >= 100 ? 100 : null;

            return number + (suffixes[a] || suffixes[b] || suffixes[c]);
        },
        week : {
            dow : 1, // Monday is the first day of the week.
            doy : 7  // The week that contains Jan 1st is the first week of the year.
        }
    });
}));
