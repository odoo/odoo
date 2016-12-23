(function( factory ) {
	if ( typeof define === "function" && define.amd ) {
		define( ["jquery", "../jquery.validate"], factory );
	} else {
		factory( jQuery );
	}
}(function( $ ) {

/*
 * Translated default messages for the jQuery validation plugin.
 * Locale: TR (Turkish; Türkçe)
 */
$.extend($.validator.messages, {
	required: "Bu alanın doldurulması zorunludur.",
	remote: "Lütfen bu alanı düzeltin.",
	email: "Lütfen geçerli bir e-posta adresi giriniz.",
	url: "Lütfen geçerli bir web adresi (URL) giriniz.",
	date: "Lütfen geçerli bir tarih giriniz.",
	dateISO: "Lütfen geçerli bir tarih giriniz(ISO formatında)",
	number: "Lütfen geçerli bir sayı giriniz.",
	digits: "Lütfen sadece sayısal karakterler giriniz.",
	creditcard: "Lütfen geçerli bir kredi kartı giriniz.",
	equalTo: "Lütfen aynı değeri tekrar giriniz.",
	extension: "Lütfen geçerli uzantıya sahip bir değer giriniz.",
	maxlength: $.validator.format("Lütfen en fazla {0} karakter uzunluğunda bir değer giriniz."),
	minlength: $.validator.format("Lütfen en az {0} karakter uzunluğunda bir değer giriniz."),
	rangelength: $.validator.format("Lütfen en az {0} ve en fazla {1} uzunluğunda bir değer giriniz."),
	range: $.validator.format("Lütfen {0} ile {1} arasında bir değer giriniz."),
	max: $.validator.format("Lütfen {0} değerine eşit ya da daha küçük bir değer giriniz."),
	min: $.validator.format("Lütfen {0} değerine eşit ya da daha büyük bir değer giriniz."),
	require_from_group: "Lütfen bu alanların en az {0} tanesini doldurunuz."
});

}));