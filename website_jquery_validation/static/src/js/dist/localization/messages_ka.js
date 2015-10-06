(function( factory ) {
	if ( typeof define === "function" && define.amd ) {
		define( ["jquery", "../jquery.validate"], factory );
	} else {
		factory( jQuery );
	}
}(function( $ ) {

/*
 * Translated default messages for the jQuery validation plugin.
 * Locale: KA (Georgian; ქართული)
 */
$.extend($.validator.messages, {
	required: "ამ ველის შევსება აუცილებელია.",
	remote: "გთხოვთ მიუთითოთ სწორი მნიშვნელობა.",
	email: "გთხოვთ მიუთითოთ ელ-ფოსტის კორექტული მისამართი.",
	url: "გთხოვთ მიუთითოთ კორექტული URL.",
	date: "გთხოვთ მიუთითოთ კორექტული თარიღი.",
	dateISO: "გთხოვთ მიუთითოთ კორექტული თარიღი ISO ფორმატში.",
	number: "გთხოვთ მიუთითოთ ციფრი.",
	digits: "გთხოვთ მიუთითოთ მხოლოდ ციფრები.",
	creditcard: "გთხოვთ მიუთითოთ საკრედიტო ბარათის კორექტული ნომერი.",
	equalTo: "გთხოვთ მიუთითოთ ასეთივე მნიშვნელობა კიდევ ერთხელ.",
	extension: "გთხოვთ აირჩიოთ ფაილი კორექტული გაფართოებით.",
	maxlength: $.validator.format("დასაშვებია არაუმეტეს {0} სიმბოლო."),
	minlength: $.validator.format("აუცილებელია შეიყვანოთ მინიმუმ {0} სიმბოლო."),
	rangelength: $.validator.format("ტექსტში სიმბოლოების რაოდენობა უნდა იყოს {0}-დან {1}-მდე."),
	range: $.validator.format("გთხოვთ შეიყვანოთ ციფრი {0}-დან {1}-მდე."),
	max: $.validator.format("გთხოვთ შეიყვანოთ ციფრი რომელიც ნაკლებია ან უდრის {0}-ს."),
	min: $.validator.format("გთხოვთ შეიყვანოთ ციფრი რომელიც მეტია ან უდრის {0}-ს.")
});

}));