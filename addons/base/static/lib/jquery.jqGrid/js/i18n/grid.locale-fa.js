;(function ($) {
/**
 * jqGrid Persian Translation
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
	$.jgrid = {
        defaults: {
            recordtext: "نمابش {0} - {1} از {2}",
            emptyrecords: "رکوردی یافت نشد",
            loadtext: "بارگزاري...",
            pgtext: "صفحه {0} از {1}"
        },
        search: {
            caption: "جستجو...",
            Find: "يافته ها",
            Reset: "از نو",
            odata: ['برابر', 'نا برابر', 'به', 'کوچکتر', 'از', 'بزرگتر', 'شروع با', 'شروع نشود با', 'نباشد', 'عضو این نباشد', 'اتمام با', 'تمام نشود با', 'حاوی', 'نباشد حاوی'],
            groupOps: [{
                op: "AND",
                text: "کل"
            },
            {
                op: "OR",
                text: "مجموع"
            }],
            matchText: " حاوی",
            rulesText: " اطلاعات"
        },
        edit: {
            addCaption: "اضافه کردن رکورد",
            editCaption: "ويرايش رکورد",
            bSubmit: "ثبت",
            bCancel: "انصراف",
            bClose: "بستن",
            saveData: "دیتا تعییر کرد! ذخیره شود؟",
            bYes: "بله",
            bNo: "خیر",
            bExit: "انصراف",
            msg: {
                required: "فيلدها بايد ختما پر شوند",
                number: "لطفا عدد وعتبر وارد کنيد",
                minValue: "مقدار وارد شده بايد بزرگتر يا مساوي با",
                maxValue: "مقدار وارد شده بايد کوچکتر يا مساوي",
                email: "پست الکترونيک وارد شده معتبر نيست",
                integer: "لطفا يک عدد صحيح وارد کنيد",
                date: "لطفا يک تاريخ معتبر وارد کنيد",
                url: "این آدرس صحیح نمی باشد. پیشوند نیاز است ('http://' یا 'https://')",
                nodefined: " تعریف نشده!",
                novalue: " مقدار برگشتی اجباری است!",
                customarray: "تابع شما باید مقدار آرایه داشته باشد!",
                customfcheck: "برای داشتن متد دلخواه شما باید سطون با چکینگ دلخواه داشته باشید!"
            }
        },
        view: {
            caption: "نمایش رکورد",
            bClose: "بستن"
        },
        del: {
            caption: "حذف",
            msg: "از حذف گزينه هاي انتخاب شده مطمئن هستيد؟",
            bSubmit: "حذف",
            bCancel: "ابطال"
        },
        nav: {
            edittext: " ",
            edittitle: "ويرايش رديف هاي انتخاب شده",
            addtext: " ",
            addtitle: "افزودن رديف جديد",
            deltext: " ",
            deltitle: "حذف ردبف هاي انتخاب شده",
            searchtext: " ",
            searchtitle: "جستجوي رديف",
            refreshtext: "",
            refreshtitle: "بازيابي مجدد صفحه",
            alertcap: "اخطار",
            alerttext: "لطفا يک رديف انتخاب کنيد",
            viewtext: "",
            viewtitle: "نمایش رکورد های انتخاب شده"
        },
        col: {
            caption: "نمايش/عدم نمايش ستون",
            bSubmit: "ثبت",
            bCancel: "انصراف"
        },
        errors: {
            errcap: "خطا",
            nourl: "هيچ آدرسي تنظيم نشده است",
            norecords: "هيچ رکوردي براي پردازش موجود نيست",
            model: "طول نام ستون ها محالف ستون هاي مدل مي باشد!"
        },
        formatter: {
            integer: {
                thousandsSeparator: " ",
                defaultValue: "0"
            },
            number: {
                decimalSeparator: ".",
                thousandsSeparator: " ",
                decimalPlaces: 2,
                defaultValue: "0.00"
            },
            currency: {
                decimalSeparator: ".",
                thousandsSeparator: " ",
                decimalPlaces: 2,
                prefix: "",
                suffix: "",
                defaultValue: "0"
            },
            date: {
                dayNames: ["يک", "دو", "سه", "چهار", "پنج", "جمع", "شنب", "يکشنبه", "دوشنبه", "سه شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه"],
                monthNames: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "ژانويه", "فوريه", "مارس", "آوريل", "مه", "ژوئن", "ژوئيه", "اوت", "سپتامبر", "اکتبر", "نوامبر", "December"],
                AmPm: ["ب.ظ", "ب.ظ", "ق.ظ", "ق.ظ"],
                S: function (b) {
                    return b < 11 || b > 13 ? ["st", "nd", "rd", "th"][Math.min((b - 1) % 10, 3)] : "th"
                },
                srcformat: "Y-m-d",
                newformat: "d/m/Y",
                masks: {
                    ISO8601Long: "Y-m-d H:i:s",
                    ISO8601Short: "Y-m-d",
                    ShortDate: "n/j/Y",
                    LongDate: "l, F d, Y",
                    FullDateTime: "l, F d, Y g:i:s A",
                    MonthDay: "F d",
                    ShortTime: "g:i A",
                    LongTime: "g:i:s A",
                    SortableDateTime: "Y-m-d\\TH:i:s",
                    UniversalSortableDateTime: "Y-m-d H:i:sO",
                    YearMonth: "F, Y"
                },
                reformatAfterEdit: false
            },
            baseLinkUrl: "",
            showAction: "نمايش",
            target: "",
            checkbox: {
                disabled: true
            },
            idName: "id"
        }
    }
})(jQuery);