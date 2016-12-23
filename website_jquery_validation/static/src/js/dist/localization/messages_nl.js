(function( factory ) {
	if ( typeof define === "function" && define.amd ) {
		define( ["jquery", "../jquery.validate"], factory );
	} else {
		factory( jQuery );
	}
}(function( $ ) {

/*
 * Translated default messages for the jQuery validation plugin.
 * Locale: NL (Dutch; Nederlands, Vlaams)
 */
$.extend($.validator.messages, {
	required: "Dit is een verplicht veld.",
	remote: "Controleer dit veld.",
	email: "Vul hier een geldig e-mailadres in.",
	url: "Vul hier een geldige URL in.",
	date: "Vul hier een geldige datum in.",
	dateISO: "Vul hier een geldige datum in (ISO-formaat).",
	number: "Vul hier een geldig getal in.",
	digits: "Vul hier alleen getallen in.",
	creditcard: "Vul hier een geldig creditcardnummer in.",
	equalTo: "Vul hier dezelfde waarde in.",
	extension: "Vul hier een waarde in met een geldige extensie.",
	maxlength: $.validator.format("Vul hier maximaal {0} tekens in."),
	minlength: $.validator.format("Vul hier minimaal {0} tekens in."),
	rangelength: $.validator.format("Vul hier een waarde in van minimaal {0} en maximaal {1} tekens."),
	range: $.validator.format("Vul hier een waarde in van minimaal {0} en maximaal {1}."),
	max: $.validator.format("Vul hier een waarde in kleiner dan of gelijk aan {0}."),
	min: $.validator.format("Vul hier een waarde in groter dan of gelijk aan {0}."),

	// for validations in additional-methods.js
	iban: "Vul hier een geldig IBAN in.",
	dateNL: "Vul hier een geldige datum in.",
	phoneNL: "Vul hier een geldig Nederlands telefoonnummer in.",
	mobileNL: "Vul hier een geldig Nederlands mobiel telefoonnummer in.",
	postalcodeNL: "Vul hier een geldige postcode in.",
	bankaccountNL: "Vul hier een geldig bankrekeningnummer in.",
	giroaccountNL: "Vul hier een geldig gironummer in.",
	bankorgiroaccountNL: "Vul hier een geldig bank- of gironummer in."
});

}));