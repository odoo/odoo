Date.CultureInfo = {
    /* Culture Name */
    name: "ar-DZ",
    englishName: "Arabic (Algeria)",
    nativeName: "العربية (الجزائر)",
   
    /* Day Name Strings */
    dayNames: ["الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"],
    abbreviatedDayNames: ["أحد", "إثنين", "ثلاثاء", "أربعاء", "خميس", "جمعة", "سبت"],
    shortestDayNames: ["حد", "ثن", "ثل", "رع", "خم", "جم", "سب"],
    firstLetterDayNames: ["ح", "ن", "ث", "ر", "خ", "ج", "س"],
    
    /* Month Name Strings */
    monthNames: ["جانفييه", "فيفرييه", "مارس", "أفريل", "مي", "جوان", "جوييه", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
    abbreviatedMonthNames: ["جان", "فيف", "مار", "أفر", "مي", "جوا", "جوي", "أوت", "سبت", "اكت", "نوف", "ديس"],

    /* AM/PM Designators */
    amDesignator: "ص",
    pmDesignator: "م",

    firstDayOfWeek: 7,
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
        shortDate: "dd/MM/yy",
        longDate: "dd/MMMM/yyyy",
        shortTime: "hh:mm tt",
        longTime: "hh:mm:ss tt",
        fullDateTime: "dd/MMMM/yyyy hh:mm:ss tt",
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
        jan: /^جان(فييه)?/i,
        feb: /^فيف(رييه)?/i,
        mar: /^مار(س)?/i,
        apr: /^أفر(يل)?/i,
        may: /^مي/i,
        jun: /^جوا(ن)?/i,
        jul: /^جوي(يه)/i,
        aug: /^أغس(طس)?/i,
        sep: /^سبت(مبر)?/i,
        oct: /^أكت(وبر)?/i,
        nov: /^نوف(مبر)?/i,
        dec: /^ديس(مبر)?/i,
        
	sun: /^الأحد|(أ|ا)حد|ح(د)?/i,
        mon: /^الإثنين|(إ|ا)ثنين|(ث)?ن/i,
        tue: /^الثلاثاء|ث(ل|لاثاء)?/i,
        wed: /^الأربعاء|(أ|ا)ربعاء|ر(ع)?/i,
        thu: /^الخميس|خ(م|ميس)?/i,
        fri: /^الجمعة|ج(م|معة)?/i,
        sat: /^السبت|س(ب|بت)?/i,

        future: /^القادم/i,
        past: /^الماضي/i,
        add: /^(\+|بعد|عقب)/i,
        subtract: /^(\-|قبل|منذ)/i,

        yesterday: /^((ال)?(ا|أ)مس|(ال)?بارح(ة)?)/i,
        today: /^اليوم/i,
        tomorrow: /^(الغد|غد(ا)?)/i,
        now: /^(ال)?آن/i,
        
        millisecond: /^(ال)?ج(زء(ا))?( من( ال(أ|ا)لف من)? |( )?.( )?)(ال)?ث(انية)?(.)?/i,
	second: /^(ال)?ث(انية|وان(ي)?)?(.)?/i,
	minute: /^(ال)?د(قيقة|قائق)?(.)?/i,
	hour: /^(ال)?س(اعة|اعات)?(.)?/i,
	week: /^(ال)?(إ|ا)س(بوع|ابيع)/i,
	month: /^(ال)?((أ|ا)?شهر|شهور)/i,
	day: /(ال)?(يوم|أيام)/i,
	year: /^(ال)?سن(ة|ين|ون|وات)/i,
		
	shortMeridian: /^(ص|م)/i,
	longMeridian: /^(صباح(ا)?|مساء(ا)?)/i,
	timezone: /^(((gmt)?\s*(\+|\-)\s*\d\d\d\d?)|gmt|utc|((ب(ال)?)?توقيت )?((ال)?(جمهورية )?(ال)?جزائر(ية)?|وسط أوروبا|cet|(central)? european tim(e|ing)))/i,        ordinalSuffix: /^\s*(st|nd|rd|th)/i,
        ordinalSuffix: /^\s*(st|nd|rd|th)/i,
        timeContext: /^\s*(\:|a(?!u|p)|p)/i
    },

	timezones: [{name:"UTC", offset:"+000"}, {name:"GMT", offset:"+000"}, {name:"CET", offset:"+0100"}]
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
 * about               قرابة
 * ago                 مضت
 * date                التاريخ
 * time                الوقت
 * calendar            التقويم
 * show                اظهار
 * hourly              كل ساعة
 * daily               يومياً
 * weekly              اسبوعياً
 * bi-weekly           مرتين بالإسبوع
 * fortnight           اسبوعان
 * monthly             شهرياً
 * bi-monthly          مرتين بالشهر
 * quarter             ربع
 * quarterly           كل ربع سنة
 * yearly              سنوياً
 * annual              سنوي
 * annually            سنوياً
 * annum               عام
 * again               مرة أخرى
 * between             بين
 * after               بعد
 * from now            من الآن
 * repeat              كرر
 * times               مرات
 * per                 كل
 * min (abbrev minute) د.
 * morning             صباح
 * noon                ظهيرة
 * night               ليل
 * midnight            نصف الليل
 * mid-night           نصف الليل
 * evening             مساء
 * final               ختامي
 * future              مستقبل
 * spring              ربيع
 * summer              صيف
 * fall                خريف
 * winter              شتاء
 * end of              نهاية
 * end                 نهاية
 * long                طويل
 * short               قصير
 */
