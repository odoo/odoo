;(function($){
/**
 * jqGrid Russian Translation v1.0 02.07.2009 (based on translation by Alexey Kanaev v1.1 21.01.2009, http://softcore.com.ru)
 * Sergey Dyagovchenko
 * http://d.sumy.ua
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
$.jgrid = {
	defaults : {
		recordtext: "Просмотр {0} - {1} из {2}",
	  emptyrecords: "Нет записей для просмотра",
		loadtext: "Загрузка...",
		pgtext : "Стр. {0} из {1}"
	},
	search : {
    caption: "Поиск...",
    Find: "Найти",
    Reset: "Сброс",
    odata : ['равно', 'не равно', 'меньше', 'меньше или равно','больше','больше или равно', 'начинается с','не начинается с','находится в','не находится в','заканчивается на','не заканчивается на','содержит','не содержит'],
    groupOps: [	{ op: "AND", text: "все" },	{ op: "OR",  text: "любой" }	],
    matchText: " совпадает",
    rulesText: " правила"
	},
	edit : {
    addCaption: "Добавить запись",
    editCaption: "Редактировать запись",
    bSubmit: "Сохранить",
    bCancel: "Отмена",
		bClose: "Закрыть",
		saveData: "Данные были измененны! Сохранить изменения?",
		bYes : "Да",
		bNo : "Нет",
		bExit : "Отмена",
	    msg: {
        required:"Поле является обязательным",
        number:"Пожалуйста, введите правильное число",
        minValue:"значение должно быть больше либо равно",
        maxValue:"значение должно быть меньше либо равно",
        email: "некорректное значение e-mail",
        integer: "Пожалуйста, введите целое число",
        date: "Пожалуйста, введите правильную дату",
        url: "неверная ссылка. Необходимо ввести префикс ('http://' or 'https://')",
		nodefined : " is not defined!",
		novalue : " return value is required!",
		customarray : "Custom function should return array!",
		customfcheck : "Custom function should be present in case of custom checking!"
		}
	},
	view : {
	    caption: "Просмотр записи",
	    bClose: "Закрыть"
	},
	del : {
	    caption: "Удалить",
	    msg: "Удалить выбранную запись(и)?",
	    bSubmit: "Удалить",
	    bCancel: "Отмена"
	},
	nav : {
  		edittext: " ",
	    edittitle: "Редактировать выбранную запись",
  		addtext:" ",
	    addtitle: "Добавить новую запись",
	    deltext: " ",
	    deltitle: "Удалить выбранную запись",
	    searchtext: " ",
	    searchtitle: "Найти записи",
	    refreshtext: "",
	    refreshtitle: "Обновить таблицу",
	    alertcap: "Внимание",
	    alerttext: "Пожалуйста, выберите запись",
  		viewtext: "",
  		viewtitle: "Просмотреть выбранную запись"
	},
	col : {
	    caption: "Показать/скрыть столбцы",
	    bSubmit: "Сохранить",
	    bCancel: "Отмена"	
	},
	errors : {
		errcap : "Ошибка",
		nourl : "URL не установлен",
		norecords: "Нет записей для обработки",
    model : "Число полей не соответствует числу столбцов таблицы!"
	},
	formatter : {
		integer : {thousandsSeparator: " ", defaultValue: '0'},
		number : {decimalSeparator:",", thousandsSeparator: " ", decimalPlaces: 2, defaultValue: '0,00'},
		currency : {decimalSeparator:",", thousandsSeparator: " ", decimalPlaces: 2, prefix: "", suffix:"", defaultValue: '0,00'},
		date : {
			dayNames:   [
				"Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб",
				"Воскресение", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"
			],
			monthNames: [
				"Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек",
				"Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
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
