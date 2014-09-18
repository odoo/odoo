Date.CultureInfo = {
	/* Culture Name */
    name: "pa-IN",
    englishName: "Punjabi (India)",
    nativeName: "ਪੰਜਾਬੀ (ਭਾਰਤ)",
    
    /* Day Name Strings */
    dayNames: ["ਐਤਵਾਰ", "ਸੋਮਵਾਰ", "ਮੰਗਲਵਾਰ", "ਬੁਧਵਾਰ", "ਵੀਰਵਾਰ", "ਸ਼ੁੱਕਰਵਾਰ", "ਸ਼ਨੀਚਰਵਾਰ"],
    abbreviatedDayNames: ["ਐਤ.", "ਸੋਮ.", "ਮੰਗਲ.", "ਬੁਧ.", "ਵੀਰ.", "ਸ਼ੁਕਰ.", "ਸ਼ਨੀ."],
    shortestDayNames: ["ਐ", "ਸ", "ਮ", "ਬ", "ਵ", "ਸ਼", "ਸ਼"],
    firstLetterDayNames: ["ਐ", "ਸ", "ਮ", "ਬ", "ਵ", "ਸ਼", "ਸ਼"],
    
    /* Month Name Strings */
    monthNames: ["ਜਨਵਰੀ", "ਫ਼ਰਵਰੀ", "ਮਾਰਚ", "ਅਪ੍ਰੈਲ", "ਮਈ", "ਜੂਨ", "ਜੁਲਾਈ", "ਅਗਸਤ", "ਸਤੰਬਰ", "ਅਕਤੂਬਰ", "ਨਵੰਬਰ", "ਦਸੰਬਰ"],
    abbreviatedMonthNames: ["ਜਨਵਰੀ", "ਫ਼ਰਵਰੀ", "ਮਾਰਚ", "ਅਪ੍ਰੈਲ", "ਮਈ", "ਜੂਨ", "ਜੁਲਾਈ", "ਅਗਸਤ", "ਸਤੰਬਰ", "ਅਕਤੂਬਰ", "ਨਵੰਬਰ", "ਦਸੰਬਰ"],

	/* AM/PM Designators */
    amDesignator: "ਸਵੇਰੇ",
    pmDesignator: "ਸ਼ਾਮ",

    firstDayOfWeek: 1,
    twoDigitYearMax: 2029,
    
    /**
     * The dateElementOrder is based on the order of the 
     * format specifiers in the formatPatterns.DatePattern. 
     *
     * Example:
     <pre>
     shortDatePattern    dateElementOrder
     ------------------  ---------------- 
     "M/d/yyyy"          "mdy"
     "dd/MM/yyyy"        "dmy"
     "yyyy-MM-dd"        "ymd"
     </pre>
     *
     * The correct dateElementOrder is required by the parser to
     * determine the expected order of the date elements in the
     * string being parsed.
     */
    dateElementOrder: "dmy",
    
    /* Standard date and time format patterns */
    formatPatterns: {
        shortDate: "dd-MM-yy",
        longDate: "dd MMMM yyyy dddd",
        shortTime: "tt hh:mm",
        longTime: "tt hh:mm:ss",
        fullDateTime: "dd MMMM yyyy dddd tt hh:mm:ss",
        sortableDateTime: "yyyy-MM-ddTHH:mm:ss",
        universalSortableDateTime: "yyyy-MM-dd HH:mm:ssZ",
        rfc1123: "ddd, dd MMM yyyy HH:mm:ss GMT",
        monthDay: "dd MMMM",
        yearMonth: "MMMM, yyyy"
    },

    /**
     * NOTE: If a string format is not parsing correctly, but
     * you would expect it parse, the problem likely lies below. 
     * 
     * The following regex patterns control most of the string matching
     * within the parser.
     * 
     * The Month name and Day name patterns were automatically generated
     * and in general should be (mostly) correct. 
     *
     * Beyond the month and day name patterns are natural language strings.
     * Example: "next", "today", "months"
     *
     * These natural language string may NOT be correct for this culture. 
     * If they are not correct, please translate and edit this file
     * providing the correct regular expression pattern. 
     *
     * If you modify this file, please post your revised CultureInfo file
     * to the Datejs Forum located at http://www.datejs.com/forums/.
     *
     * Please mark the subject of the post with [CultureInfo]. Example:
     *    Subject: [CultureInfo] Translated "da-DK" Danish(Denmark)
     * 
     * We will add the modified patterns to the master source files.
     *
     * As well, please review the list of "Future Strings" section below. 
     */	
    regexPatterns: {
        jan: /^ਜਨਵਰੀ/i,
        feb: /^ਫ਼ਰਵਰੀ/i,
        mar: /^ਮਾਰਚ/i,
        apr: /^ਅਪ੍ਰੈਲ/i,
        may: /^ਮਈ/i,
        jun: /^ਜੂਨ/i,
        jul: /^ਜੁਲਾਈ/i,
        aug: /^ਅਗਸਤ/i,
        sep: /^ਸਤੰਬਰ/i,
        oct: /^ਅਕਤੂਬਰ/i,
        nov: /^ਨਵੰਬਰ/i,
        dec: /^ਦਸੰਬਰ/i,

        sun: /^ਐ(ਤ(.(ਵਾਰ)?)?)?/i,
        mon: /^ਸ(ੋਮ(.(ਵਾਰ)?)?)?/i,
        tue: /^ਮ(ੰਗਲ(.(ਵਾਰ)?)?)?/i,
        wed: /^ਬ(ੁਧ(.(ਵਾਰ)?)?)?/i,
        thu: /^ਵ(ੀਰ(.(ਵਾਰ)?)?)?/i,
        fri: /^ਸ਼(ੁਕਰ(.(ਰਵਾਰ)?)?)?/i,
        sat: /^ਸ਼(ਨੀ(.(ਚਰਵਾਰ)?)?)?/i,

        future: /^next/i,
        past: /^last|past|prev(ious)?/i,
        add: /^(\+|aft(er)?|from|hence)/i,
        subtract: /^(\-|bef(ore)?|ago)/i,
        
        yesterday: /^yes(terday)?/i,
        today: /^t(od(ay)?)?/i,
        tomorrow: /^tom(orrow)?/i,
        now: /^n(ow)?/i,
        
        millisecond: /^ms|milli(second)?s?/i,
        second: /^sec(ond)?s?/i,
        minute: /^mn|min(ute)?s?/i,
		hour: /^h(our)?s?/i,
		week: /^w(eek)?s?/i,
        month: /^m(onth)?s?/i,
        day: /^d(ay)?s?/i,
        year: /^y(ear)?s?/i,
		
        shortMeridian: /^(a|p)/i,
        longMeridian: /^(a\.?m?\.?|p\.?m?\.?)/i,
        timezone: /^((e(s|d)t|c(s|d)t|m(s|d)t|p(s|d)t)|((gmt)?\s*(\+|\-)\s*\d\d\d\d?)|gmt|utc)/i,
        ordinalSuffix: /^\s*(st|nd|rd|th)/i,
        timeContext: /^\s*(\:|a(?!u|p)|p)/i
    },

	timezones: [{name:"UTC", offset:"-000"}, {name:"GMT", offset:"-000"}, {name:"EST", offset:"-0500"}, {name:"EDT", offset:"-0400"}, {name:"CST", offset:"-0600"}, {name:"CDT", offset:"-0500"}, {name:"MST", offset:"-0700"}, {name:"MDT", offset:"-0600"}, {name:"PST", offset:"-0800"}, {name:"PDT", offset:"-0700"}]
};

/********************
 ** Future Strings **
 ********************
 * 
 * The following list of strings may not be currently being used, but 
 * may be incorporated into the Datejs library later. 
 *
 * We would appreciate any help translating the strings below.
 * 
 * If you modify this file, please post your revised CultureInfo file
 * to the Datejs Forum located at http://www.datejs.com/forums/.
 *
 * Please mark the subject of the post with [CultureInfo]. Example:
 *    Subject: [CultureInfo] Translated "da-DK" Danish(Denmark)b
 *
 * English Name        Translated
 * ------------------  -----------------
 * about               about
 * ago                 ago
 * date                date
 * time                time
 * calendar            calendar
 * show                show
 * hourly              hourly
 * daily               daily
 * weekly              weekly
 * bi-weekly           bi-weekly
 * fortnight           fortnight
 * monthly             monthly
 * bi-monthly          bi-monthly
 * quarter             quarter
 * quarterly           quarterly
 * yearly              yearly
 * annual              annual
 * annually            annually
 * annum               annum
 * again               again
 * between             between
 * after               after
 * from now            from now
 * repeat              repeat
 * times               times
 * per                 per
 * min (abbrev minute) min
 * morning             morning
 * noon                noon
 * night               night
 * midnight            midnight
 * mid-night           mid-night
 * evening             evening
 * final               final
 * future              future
 * spring              spring
 * summer              summer
 * fall                fall
 * winter              winter
 * end of              end of
 * end                 end
 * long                long
 * short               short
 */