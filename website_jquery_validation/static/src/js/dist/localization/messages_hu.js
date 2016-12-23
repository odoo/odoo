(function( factory ) {
	if ( typeof define === "function" && define.amd ) {
		define( ["jquery", "../jquery.validate"], factory );
	} else {
		factory( jQuery );
	}
}(function( $ ) {

/*
 * Translated default messages for the jQuery validation plugin.
 * Locale: HU (Hungarian; Magyar)
 */
$.extend($.validator.messages, {
	required: "Kötelező megadni.",
	maxlength: $.validator.format("Legfeljebb {0} karakter hosszú legyen."),
	minlength: $.validator.format("Legalább {0} karakter hosszú legyen."),
	rangelength: $.validator.format("Legalább {0} és legfeljebb {1} karakter hosszú legyen."),
	email: "Érvényes e-mail címnek kell lennie.",
	url: "Érvényes URL-nek kell lennie.",
	date: "Dátumnak kell lennie.",
	number: "Számnak kell lennie.",
	digits: "Csak számjegyek lehetnek.",
	equalTo: "Meg kell egyeznie a két értéknek.",
	range: $.validator.format("{0} és {1} közé kell esnie."),
	max: $.validator.format("Nem lehet nagyobb, mint {0}."),
	min: $.validator.format("Nem lehet kisebb, mint {0}."),
	creditcard: "Érvényes hitelkártyaszámnak kell lennie.",
	remote: "Kérem javítsa ki ezt a mezőt.",
	dateISO: "Kérem írjon be egy érvényes dátumot (ISO)."
});

}));