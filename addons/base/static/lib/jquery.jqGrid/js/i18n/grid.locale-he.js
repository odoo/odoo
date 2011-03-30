;(function($){
/**
 * jqGrid Hebrew Translation
 * Shuki Shukrun shukrun.shuki@gmail.com
 * http://trirand.com/blog/ 
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
$.jgrid = {
	defaults : {
		recordtext: "מציג {0} - {1} מתוך {2}",
		emptyrecords: "אין רשומות להציג",
		loadtext: "טוען...",
		pgtext : "דף {0} מתוך {1}"
	},
	search : {
		caption: "מחפש...",
		Find: "חפש",
		Reset: "התחל",
		odata : ['שווה', 'לא שווה', 'קטן', 'קטן או שווה','גדול','גדול או שווה', 'מתחיל ב','לא מתחיל ב','נמצא ב','לא נמצא ב','מסתיים ב','לא מסתיים ב','מכיל','לא מכיל'],
		groupOps: [	{ op: "AND", text: "הכל" },	{ op: "OR",  text: "אחד מ" }	],
		matchText: " תואם",
		rulesText: " חוקים"
	},
	edit : {
		addCaption: "הוסף רשומה",
		editCaption: "ערוך רשומה",
		bSubmit: "שלח",
		bCancel: "בטל",
		bClose: "סגור",
		saveData: "נתונים השתנו! לשמור?",
		bYes : "כן",
		bNo : "לא",
		bExit : "בטל",
		msg: {
			required:"שדה חובה",
			number:"אנא, הכנס מספר תקין",
			minValue:"ערך צריך להיות גדול או שווה ל ",
			maxValue:"ערך צריך להיות קטן או שווה ל ",
			email: "היא לא כתובת איימל תקינה",
			integer: "אנא, הכנס מספר שלם",
			date: "אנא, הכנס תאריך תקין",
			url: "הכתובת אינה תקינה. דרושה תחילית ('http://' או 'https://')",
			nodefined : " is not defined!",
			novalue : " return value is required!",
			customarray : "Custom function should return array!",
			customfcheck : "Custom function should be present in case of custom checking!"
		}
	},
	view : {
		caption: "הצג רשומה",
		bClose: "סגור"
	},
	del : {
		caption: "מחק",
		msg: "האם למחוק את הרשומה/ות המסומנות?",
		bSubmit: "מחק",
		bCancel: "בטל"
	},
	nav : {
		edittext: "",
		edittitle: "ערוך שורה מסומנת",
		addtext:"",
		addtitle: "הוסף שורה חדשה",
		deltext: "",
		deltitle: "מחק שורה מסומנת",
		searchtext: "",
		searchtitle: "חפש רשומות",
		refreshtext: "",
		refreshtitle: "טען גריד מחדש",
		alertcap: "אזהרה",
		alerttext: "אנא, בחר שורה",
		viewtext: "",
		viewtitle: "הצג שורה מסומנת"
	},
	col : {
		caption: "הצג/הסתר עמודות",
		bSubmit: "שלח",
		bCancel: "בטל"
	},
	errors : {
		errcap : "שגיאה",
		nourl : "לא הוגדרה כתובת url",
		norecords: "אין רשומות לעבד",
		model : "אורך של colNames <> colModel!"
	},
	formatter : {
		integer : {thousandsSeparator: " ", defaultValue: '0'},
		number : {decimalSeparator:".", thousandsSeparator: " ", decimalPlaces: 2, defaultValue: '0.00'},
		currency : {decimalSeparator:".", thousandsSeparator: " ", decimalPlaces: 2, prefix: "", suffix:"", defaultValue: '0.00'},
		date : {
			dayNames:   [
				"א", "ב", "ג", "ד", "ה", "ו", "ש",
				"ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"
			],
			monthNames: [
				"ינו", "פבר", "מרץ", "אפר", "מאי", "יונ", "יול", "אוג", "ספט", "אוק", "נוב", "דצמ",
				"ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"
			],
			AmPm : ["לפני הצהרים","אחר הצהרים","לפני הצהרים","אחר הצהרים"],
			S: function (j) {return j < 11 || j > 13 ? ['', '', '', ''][Math.min((j - 1) % 10, 3)] : ''},
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
