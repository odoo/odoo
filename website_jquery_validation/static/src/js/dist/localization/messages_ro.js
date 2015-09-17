(function( factory ) {
	if ( typeof define === "function" && define.amd ) {
		define( ["jquery", "../jquery.validate"], factory );
	} else {
		factory( jQuery );
	}
}(function( $ ) {

/*
 * Translated default messages for the jQuery validation plugin.
 * Locale: RO (Romanian, limba română)
 */
$.extend($.validator.messages, {
	required: "Acest câmp este obligatoriu.",
	remote: "Te rugăm să completezi acest câmp.",
	email: "Te rugăm să introduci o adresă de email validă",
	url: "Te rugăm sa introduci o adresă URL validă.",
	date: "Te rugăm să introduci o dată corectă.",
	dateISO: "Te rugăm să introduci o dată (ISO) corectă.",
	number: "Te rugăm să introduci un număr întreg valid.",
	digits: "Te rugăm să introduci doar cifre.",
	creditcard: "Te rugăm să introduci un numar de carte de credit valid.",
	equalTo: "Te rugăm să reintroduci valoarea.",
	extension: "Te rugăm să introduci o valoare cu o extensie validă.",
	maxlength: $.validator.format("Te rugăm să nu introduci mai mult de {0} caractere."),
	minlength: $.validator.format("Te rugăm să introduci cel puțin {0} caractere."),
	rangelength: $.validator.format("Te rugăm să introduci o valoare între {0} și {1} caractere."),
	range: $.validator.format("Te rugăm să introduci o valoare între {0} și {1}."),
	max: $.validator.format("Te rugăm să introduci o valoare egal sau mai mică decât {0}."),
	min: $.validator.format("Te rugăm să introduci o valoare egal sau mai mare decât {0}.")
});

}));