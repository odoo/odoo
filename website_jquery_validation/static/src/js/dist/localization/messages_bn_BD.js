(function( factory ) {
	if ( typeof define === "function" && define.amd ) {
		define( ["jquery", "../jquery.validate"], factory );
	} else {
		factory( jQuery );
	}
}(function( $ ) {

/*
 * Translated default messages for the jQuery validation plugin.
 * Locale: bn_BD (Bengali, Bangladesh)
 */
$.extend($.validator.messages, {
	required: "এই তথ্যটি আবশ্যক।",
	remote: "এই তথ্যটি ঠিক করুন।",
	email: "অনুগ্রহ করে একটি সঠিক মেইল ঠিকানা লিখুন।",
	url: "অনুগ্রহ করে একটি সঠিক লিঙ্ক দিন।",
	date: "তারিখ সঠিক নয়।",
	dateISO: "অনুগ্রহ করে একটি সঠিক (ISO) তারিখ লিখুন।",
	number: "অনুগ্রহ করে একটি সঠিক নম্বর লিখুন।",
	digits: "এখানে শুধু সংখ্যা ব্যবহার করা যাবে।",
	creditcard: "অনুগ্রহ করে একটি ক্রেডিট কার্ডের সঠিক নম্বর লিখুন।",
	equalTo: "একই মান আবার লিখুন।",
	extension: "সঠিক ধরনের ফাইল আপলোড করুন।",
	maxlength: $.validator.format("{0}টির বেশি অক্ষর লেখা যাবে না।"),
	minlength: $.validator.format("{0}টির কম অক্ষর লেখা যাবে না।"),
	rangelength: $.validator.format("{0} থেকে {1} টি অক্ষর সম্বলিত মান লিখুন।"),
	range: $.validator.format("{0} থেকে {1} এর মধ্যে একটি মান ব্যবহার করুন।"),
	max: $.validator.format("অনুগ্রহ করে {0} বা তার চাইতে কম মান ব্যবহার করুন।"),
	min: $.validator.format("অনুগ্রহ করে {0} বা তার চাইতে বেশি মান ব্যবহার করুন।")
});

}));