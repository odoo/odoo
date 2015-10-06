(function( factory ) {
	if ( typeof define === "function" && define.amd ) {
		define( ["jquery", "../jquery.validate"], factory );
	} else {
		factory( jQuery );
	}
}(function( $ ) {

/*
 * Translated default messages for the jQuery validation plugin.
 * Locale: MY (Malay; Melayu)
 */
$.extend($.validator.messages, {
	required: "Medan ini diperlukan.",
	remote: "Sila betulkan medan ini.",
	email: "Sila masukkan alamat emel yang betul.",
	url: "Sila masukkan URL yang betul.",
	date: "Sila masukkan tarikh yang betul.",
	dateISO: "Sila masukkan tarikh(ISO) yang betul.",
	number: "Sila masukkan nombor yang betul.",
	digits: "Sila masukkan nilai digit sahaja.",
	creditcard: "Sila masukkan nombor kredit kad yang betul.",
	equalTo: "Sila masukkan nilai yang sama semula.",
	extension: "Sila masukkan nilai yang telah diterima.",
	maxlength: $.validator.format("Sila masukkan nilai tidak lebih dari {0} aksara."),
	minlength: $.validator.format("Sila masukkan nilai sekurang-kurangnya {0} aksara."),
	rangelength: $.validator.format("Sila masukkan panjang nilai antara {0} dan {1} aksara."),
	range: $.validator.format("Sila masukkan nilai antara {0} dan {1} aksara."),
	max: $.validator.format("Sila masukkan nilai yang kurang atau sama dengan {0}."),
	min: $.validator.format("Sila masukkan nilai yang lebih atau sama dengan {0}.")
});

}));