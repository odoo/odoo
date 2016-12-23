(function( factory ) {
	if ( typeof define === "function" && define.amd ) {
		define( ["jquery", "../jquery.validate"], factory );
	} else {
		factory( jQuery );
	}
}(function( $ ) {

/*
 * Translated default messages for the jQuery validation plugin.
 * Locale: HE (Hebrew; עברית)
 */
$.extend($.validator.messages, {
	required: "השדה הזה הינו שדה חובה",
	remote: "נא לתקן שדה זה",
	email: "נא למלא כתובת דוא\"ל חוקית",
	url: "נא למלא כתובת אינטרנט חוקית",
	date: "נא למלא תאריך חוקי",
	dateISO: "נא למלא תאריך חוקי (ISO)",
	number: "נא למלא מספר",
	digits: "נא למלא רק מספרים",
	creditcard: "נא למלא מספר כרטיס אשראי חוקי",
	equalTo: "נא למלא את אותו ערך שוב",
	extension: "נא למלא ערך עם סיומת חוקית",
	maxlength: $.validator.format(".נא לא למלא יותר מ- {0} תווים"),
	minlength: $.validator.format("נא למלא לפחות {0} תווים"),
	rangelength: $.validator.format("נא למלא ערך בין {0} ל- {1} תווים"),
	range: $.validator.format("נא למלא ערך בין {0} ל- {1}"),
	max: $.validator.format("נא למלא ערך קטן או שווה ל- {0}"),
	min: $.validator.format("נא למלא ערך גדול או שווה ל- {0}")
});

}));