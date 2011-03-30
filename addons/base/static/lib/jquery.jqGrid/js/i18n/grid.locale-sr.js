;(function($){
/**
 * jqGrid Serbian Translation
 * Александар Миловац(Aleksandar Milovac) aleksandar.milovac@gmail.com
 * http://trirand.com/blog/
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
$.jgrid = {
	defaults : {
		recordtext: "Преглед {0} - {1} од {2}",
		emptyrecords: "Не постоји ниједан запис",
		loadtext: "Учитавање...",
		pgtext : "Страна {0} од {1}"
	},
	search : {
		caption: "Тражење...",
		Find: "Тражи",
		Reset: "Ресетуј",
		odata : ['једнако', 'није једнако', 'мање', 'мање или једнако','веће','веће или једнако', 'почиње са','не почиње са','је у','није у','завршава са','не завршава са','садржи','не садржи'],
		groupOps: [	{ op: "И", text: "сви" },	{ op: "ИЛИ",  text: "сваки" }	],
		matchText: " match",
		rulesText: " правила"
	},
	edit : {
		addCaption: "Додај запис",
		editCaption: "Измени запис",
		bSubmit: "Пошаљи",
		bCancel: "Одустани",
		bClose: "Затвори",
		saveData: "Податак је измењен! Сачувај измене?",
		bYes : "Да",
		bNo : "Не",
		bExit : "Одустани",
		msg: {
			required:"Поље је обавезно",
			number:"Молим, унесите исправан број",
			minValue:"вредност мора бити већа од или једнака са ",
			maxValue:"вредност мора бити мања од или једнака са",
			email: "није исправна имејл адреса",
			integer: "Молим, унесите исправну целобројну вредност ",
			date: "Молим, унесите исправан датум",
			url: "није исправан УРЛ. Потребан је префикс ('http://' or 'https://')",
			nodefined : " није дефинисан!",
			novalue : " захтевана је повратна вредност!",
			customarray : "Custom function should return array!",
			customfcheck : "Custom function should be present in case of custom checking!"
			
		}
	},
	view : {
		caption: "Погледај запис",
		bClose: "Затвори"
	},
	del : {
		caption: "Избриши",
		msg: "Избриши изабран(е) запис(е)?",
		bSubmit: "Ибриши",
		bCancel: "Одбаци"
	},
	nav : {
		edittext: "",
		edittitle: "Измени изабрани ред",
		addtext:"",
		addtitle: "Додај нови ред",
		deltext: "",
		deltitle: "Избриши изабран ред",
		searchtext: "",
		searchtitle: "Нађи записе",
		refreshtext: "",
		refreshtitle: "Поново учитај податке",
		alertcap: "Упозорење",
		alerttext: "Молим, изаберите ред",
		viewtext: "",
		viewtitle: "Погледај изабрани ред"
	},
	col : {
		caption: "Изабери колоне",
		bSubmit: "ОК",
		bCancel: "Одбаци"
	},
	errors : {
		errcap : "Грешка",
		nourl : "Није постављен URL",
		norecords: "Нема записа за обраду",
		model : "Дужина модела colNames <> colModel!"
	},
	formatter : {
		integer : {thousandsSeparator: " ", defaultValue: '0'},
		number : {decimalSeparator:".", thousandsSeparator: " ", decimalPlaces: 2, defaultValue: '0.00'},
		currency : {decimalSeparator:".", thousandsSeparator: " ", decimalPlaces: 2, prefix: "", suffix:"", defaultValue: '0.00'},
		date : {
			dayNames:   [
				"Нед", "Пон", "Уто", "Сре", "Чет", "Пет", "Суб",
				"Недеља", "Понедељак", "Уторак", "Среда", "Четвртак", "Петак", "Субота"
			],
			monthNames: [
				"Јан", "Феб", "Мар", "Апр", "Мај", "Јун", "Јул", "Авг", "Сеп", "Окт", "Нов", "Дец",
				"Јануар", "Фебруар", "Март", "Април", "Мај", "Јун", "Јул", "Август", "Септембар", "Октобар", "Новембар", "Децембар"
			],
			AmPm : ["am","pm","AM","PM"],
			S: function (j) {return j < 11 || j > 13 ? ['st', 'nd', 'rd', 'th'][Math.min((j - 1) % 10, 3)] : 'th'},
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
