;(function($){
/**
 * jqGrid Ukrainian Translation v1.0 02.07.2009
 * Sergey Dyagovchenko
 * http://d.sumy.ua
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
$.jgrid = {
	defaults : {
		recordtext: "Перегляд {0} - {1} з {2}",
	  emptyrecords: "Немає записів для перегляду",
		loadtext: "Завантаження...",
		pgtext : "Стор. {0} з {1}"
	},
	search : {
    caption: "Пошук...",
    Find: "Знайти",
    Reset: "Скидання",
    odata : ['рівно', 'не рівно', 'менше', 'менше або рівне','більше','більше або рівне', 'починається з','не починається з','знаходиться в','не знаходиться в','закінчується на','не закінчується на','містить','не містить'],
    groupOps: [	{ op: "AND", text: "все" },	{ op: "OR",  text: "будь-який" }	],
    matchText: " збігається",
    rulesText: " правила"
	},
	edit : {
    addCaption: "Додати запис",
    editCaption: "Змінити запис",
    bSubmit: "Зберегти",
    bCancel: "Відміна",
		bClose: "Закрити",
		saveData: "До данних були внесені зміни! Зберегти зміни?",
		bYes : "Так",
		bNo : "Ні",
		bExit : "Відміна",
	    msg: {
        required:"Поле є обов'язковим",
        number:"Будь ласка, введіть правильне число",
        minValue:"значення повинне бути більше або дорівнює",
        maxValue:"значення повинно бути менше або дорівнює",
        email: "некоректна адреса електронної пошти",
        integer: "Будь ласка, введення дійсне ціле значення",
        date: "Будь ласка, введення дійсне значення дати",
        url: "не дійсний URL. Необхідна приставка ('http://' or 'https://')",
		nodefined : " is not defined!",
		novalue : " return value is required!",
		customarray : "Custom function should return array!",
		customfcheck : "Custom function should be present in case of custom checking!"
		}
	},
	view : {
	    caption: "Переглянути запис",
	    bClose: "Закрити"
	},
	del : {
	    caption: "Видалити",
	    msg: "Видалити обраний запис(и)?",
	    bSubmit: "Видалити",
	    bCancel: "Відміна"
	},
	nav : {
  		edittext: " ",
	    edittitle: "Змінити вибраний запис",
  		addtext:" ",
	    addtitle: "Додати новий запис",
	    deltext: " ",
	    deltitle: "Видалити вибраний запис",
	    searchtext: " ",
	    searchtitle: "Знайти записи",
	    refreshtext: "",
	    refreshtitle: "Оновити таблицю",
	    alertcap: "Попередження",
	    alerttext: "Будь ласка, виберіть запис",
  		viewtext: "",
  		viewtitle: "Переглянути обраний запис"
	},
	col : {
	    caption: "Показати/Приховати стовпці",
	    bSubmit: "Зберегти",
	    bCancel: "Відміна"
	},
	errors : {
		errcap : "Помилка",
		nourl : "URL не задан",
		norecords: "Немає записів для обробки",
    model : "Число полів не відповідає числу стовпців таблиці!"
	},
	formatter : {
		integer : {thousandsSeparator: " ", defaultValue: '0'},
		number : {decimalSeparator:",", thousandsSeparator: " ", decimalPlaces: 2, defaultValue: '0,00'},
		currency : {decimalSeparator:",", thousandsSeparator: " ", decimalPlaces: 2, prefix: "", suffix:"", defaultValue: '0,00'},
		date : {
			dayNames:   [
				"Нд", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб",
				"Неділя", "Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота"
			],
			monthNames: [
				"Січ", "Лют", "Бер", "Кві", "Тра", "Чер", "Лип", "Сер", "Вер", "Жов", "Лис", "Гру",
				"Січень", "Лютий", "Березень", "Квітень", "Травень", "Червень", "Липень", "Серпень", "Вересень", "Жовтень", "Листопад", "Грудень"
			],
			AmPm : ["am","pm","AM","PM"],
			S: function (j) {return j < 11 || j > 13 ? ['st', 'nd', 'rd', 'th'][Math.min((j - 1) % 10, 3)] : 'th'},
			srcformat: 'Y-m-d',
			newformat: 'd.m.Y',
			masks : {
	            ISO8601Long:"Y-m-d H:i:s",
	            ISO8601Short:"Y-m-d",
	            ShortDate: "n.j.Y",
	            LongDate: "l, F d, Y",
	            FullDateTime: "l, F d, Y G:i:s",
	            MonthDay: "F d",
	            ShortTime: "G:i",
	            LongTime: "G:i:s",
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
