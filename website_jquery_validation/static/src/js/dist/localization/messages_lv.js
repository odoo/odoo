(function( factory ) {
	if ( typeof define === "function" && define.amd ) {
		define( ["jquery", "../jquery.validate"], factory );
	} else {
		factory( jQuery );
	}
}(function( $ ) {

/*
 * Translated default messages for the jQuery validation plugin.
 * Locale: LV (Latvian; latviešu valoda)
 */
$.extend($.validator.messages, {
	required: "Šis lauks ir obligāts.",
	remote: "Lūdzu, pārbaudiet šo lauku.",
	email: "Lūdzu, ievadiet derīgu e-pasta adresi.",
	url: "Lūdzu, ievadiet derīgu URL adresi.",
	date: "Lūdzu, ievadiet derīgu datumu.",
	dateISO: "Lūdzu, ievadiet derīgu datumu (ISO).",
	number: "Lūdzu, ievadiet derīgu numuru.",
	digits: "Lūdzu, ievadiet tikai ciparus.",
	creditcard: "Lūdzu, ievadiet derīgu kredītkartes numuru.",
	equalTo: "Lūdzu, ievadiet to pašu vēlreiz.",
	extension: "Lūdzu, ievadiet vērtību ar derīgu paplašinājumu.",
	maxlength: $.validator.format("Lūdzu, ievadiet ne vairāk kā {0} rakstzīmes."),
	minlength: $.validator.format("Lūdzu, ievadiet vismaz {0} rakstzīmes."),
	rangelength: $.validator.format("Lūdzu ievadiet {0} līdz {1} rakstzīmes."),
	range: $.validator.format("Lūdzu, ievadiet skaitli no {0} līdz {1}."),
	max: $.validator.format("Lūdzu, ievadiet skaitli, kurš ir mazāks vai vienāds ar {0}."),
	min: $.validator.format("Lūdzu, ievadiet skaitli, kurš ir lielāks vai vienāds ar {0}.")
});

}));