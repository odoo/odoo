(function( factory ) {
	if ( typeof define === "function" && define.amd ) {
		define( ["jquery", "../jquery.validate"], factory );
	} else {
		factory( jQuery );
	}
}(function( $ ) {

/*
 * Translated default messages for the jQuery validation plugin.
 * Locale: NO (Norwegian; Norsk)
 */
$.extend($.validator.messages, {
	required: "Dette feltet er obligatorisk.",
	maxlength: $.validator.format("Maksimalt {0} tegn."),
	minlength: $.validator.format("Minimum {0} tegn."),
	rangelength: $.validator.format("Angi minimum {0} og maksimum {1} tegn."),
	email: "Oppgi en gyldig epostadresse.",
	url: "Angi en gyldig URL.",
	date: "Angi en gyldig dato.",
	dateISO: "Angi en gyldig dato (&ARING;&ARING;&ARING;&ARING;-MM-DD).",
	dateSE: "Angi en gyldig dato.",
	number: "Angi et gyldig nummer.",
	numberSE: "Angi et gyldig nummer.",
	digits: "Skriv kun tall.",
	equalTo: "Skriv samme verdi igjen.",
	range: $.validator.format("Angi en verdi mellom {0} og {1}."),
	max: $.validator.format("Angi en verdi som er mindre eller lik {0}."),
	min: $.validator.format("Angi en verdi som er st&oslash;rre eller lik {0}."),
	creditcard: "Angi et gyldig kredittkortnummer."
});

}));