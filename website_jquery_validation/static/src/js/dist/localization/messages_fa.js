(function( factory ) {
	if ( typeof define === "function" && define.amd ) {
		define( ["jquery", "../jquery.validate"], factory );
	} else {
		factory( jQuery );
	}
}(function( $ ) {

/*
 * Translated default messages for the jQuery validation plugin.
 * Locale: FA (Persian; فارسی)
 */
$.extend($.validator.messages, {
	required: "تکمیل این فیلد اجباری است.",
	remote: "لطفا این فیلد را تصحیح کنید.",
	email: ".لطفا یک ایمیل صحیح وارد کنید",
	url: "لطفا آدرس صحیح وارد کنید.",
	date: "لطفا یک تاریخ صحیح وارد کنید",
	dateFA: "لطفا یک تاریخ صحیح وارد کنید",
	dateISO: "لطفا تاریخ صحیح وارد کنید (ISO).",
	number: "لطفا عدد صحیح وارد کنید.",
	digits: "لطفا تنها رقم وارد کنید",
	creditcard: "لطفا کریدیت کارت صحیح وارد کنید.",
	equalTo: "لطفا مقدار برابری وارد کنید",
	extension: "لطفا مقداری وارد کنید که ",
	maxlength: $.validator.format("لطفا بیشتر از {0} حرف وارد نکنید."),
	minlength: $.validator.format("لطفا کمتر از {0} حرف وارد نکنید."),
	rangelength: $.validator.format("لطفا مقداری بین {0} تا {1} حرف وارد کنید."),
	range: $.validator.format("لطفا مقداری بین {0} تا {1} حرف وارد کنید."),
	max: $.validator.format("لطفا مقداری کمتر از {0} حرف وارد کنید."),
	min: $.validator.format("لطفا مقداری بیشتر از {0} حرف وارد کنید."),
	minWords: $.validator.format("لطفا حداقل {0} کلمه وارد کنید."),
	maxWords: $.validator.format("لطفا حداکثر {0} کلمه وارد کنید.")
});

}));