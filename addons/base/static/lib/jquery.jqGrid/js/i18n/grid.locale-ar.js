;(function($){
/**
 * jqGrid Arabic Translation
 * 
 * http://trirand.com/blog/ 
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
$.jgrid = {
	defaults : {
		recordtext: "تسجيل {0} - {1} على {2}",
		emptyrecords: "لا يوجد تسجيل",
		loadtext: "تحميل...",
		pgtext : "صفحة {0} على {1}"
	},
	search : {
		caption: "بحث...",
		Find: "بحث",
		Reset: "إلغاء",
		odata : ['يساوي', 'يختلف', 'أقل', 'أقل أو يساوي','أكبر','أكبر أو يساوي', 'يبدأ بـ','لا يبدأ بـ','est dans',"n'est pas dans",'ينته بـ','لا ينته بـ','يحتوي','لا يحتوي'],
		groupOps: [	{ op: "مع", text: "الكل" },	{ op: "أو",  text: "لا أحد" }	],
		matchText: " توافق",
		rulesText: " قواعد"
	},
	edit : {
		addCaption: "اضافة",
		editCaption: "تحديث",
		bSubmit: "تثبيث",
		bCancel: "إلغاء",
		bClose: "غلق",
		saveData: "تغيرت المعطيات هل تريد التسجيل ?",
		bYes: "نعم",
		bNo: "لا",
		bExit: "إلغاء",
		msg: {
			required: "خانة إجبارية",
			number: "سجل رقم صحيح",
			minValue: "يجب أن تكون القيمة أكبر أو تساوي 0",
			maxValue: "يجب أن تكون القيمة أقل أو تساوي 0",
			email: "بريد غير صحيح",
			integer: "سجل عدد طبييعي صحيح",
			url: "ليس عنوانا صحيحا. البداية الصحيحة ('http://' أو 'https://')",
			nodefined : " ليس محدد!",
			novalue : " قيمة الرجوع مطلوبة!",
			customarray : "يجب على الدالة الشخصية أن تنتج جدولا",
			customfcheck : "الدالة الشخصية مطلوبة في حالة التحقق الشخصي"
		}
	},
	view : {
		caption: "رأيت التسجيلات",
		bClose: "غلق"
	},
	del : {
		caption: "حذف",
		msg: "حذف التسجيلات المختارة ?",
		bSubmit: "حذف",
		bCancel: "إلغاء"
	},
	nav : {
		edittext: " ",
		edittitle: "تغيير التسجيل المختار",
		addtext:" ",
		addtitle: "إضافة تسجيل",
		deltext: " ",
		deltitle: "حذف التسجيل المختار",
		searchtext: " ",
		searchtitle: "بحث عن تسجيل",
		refreshtext: "",
		refreshtitle: "تحديث الجدول",
		alertcap: "تحذير",
		alerttext: "يرجى إختيار السطر",
		viewtext: "",
		viewtitle: "إظهار السطر المختار"
	},
	col : {
		caption: "إظهار/إخفاء الأعمدة",
		bSubmit: "تثبيث",
		bCancel: "إلغاء"
	},
	errors : {
		errcap : "خطأ",
		nourl : "لا يوجد عنوان محدد",
		norecords: "لا يوجد تسجيل للمعالجة",
		model : "عدد العناوين (colNames) <> عدد التسجيلات (colModel)!"
	},
	formatter : {
		integer : {thousandsSeparator: " ", defaultValue: '0'},
		number : {decimalSeparator:",", thousandsSeparator: " ", decimalPlaces: 2, defaultValue: '0,00'},
		currency : {decimalSeparator:",", thousandsSeparator: " ", decimalPlaces: 2, prefix: "", suffix:"", defaultValue: '0,00'},
		date : {
			dayNames:   [
				"الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت",
				"الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"
			],
			monthNames: [
				"جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان", "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
				"جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان", "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
			],
			AmPm : ["صباحا","مساءا","صباحا","مساءا"],
			S: function (j) {return j == 1 ? 'er' : 'e';},
			srcformat: 'Y-m-d',
			newformat: 'd/m/Y',
			masks : {
				ISO8601Long:"Y-m-d H:i:s",
				ISO8601Short:"Y-m-d",
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
			reformatAfterEdit : false
		},
		baseLinkUrl: '',
		showAction: '',
		target: '',
		checkbox : {disabled:true},
		idName : 'id'
	}
};
})(jQuery);
