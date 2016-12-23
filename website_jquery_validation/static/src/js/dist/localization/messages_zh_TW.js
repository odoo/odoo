(function( factory ) {
	if ( typeof define === "function" && define.amd ) {
		define( ["jquery", "../jquery.validate"], factory );
	} else {
		factory( jQuery );
	}
}(function( $ ) {

/*
 * Translated default messages for the jQuery validation plugin.
 * Locale: ZH (Chinese; 中文 (Zhōngwén), 汉语, 漢語)
 * Region: TW (Taiwan)
 */
$.extend($.validator.messages, {
	required: "必須填寫",
	remote: "請修正此欄位",
	email: "請輸入有效的電子郵件",
	url: "請輸入有效的網址",
	date: "請輸入有效的日期",
	dateISO: "請輸入有效的日期 (YYYY-MM-DD)",
	number: "請輸入正確的數值",
	digits: "只可輸入數字",
	creditcard: "請輸入有效的信用卡號碼",
	equalTo: "請重複輸入一次",
	extension: "請輸入有效的後綴",
	maxlength: $.validator.format("最多 {0} 個字"),
	minlength: $.validator.format("最少 {0} 個字"),
	rangelength: $.validator.format("請輸入長度為 {0} 至 {1} 之間的字串"),
	range: $.validator.format("請輸入 {0} 至 {1} 之間的數值"),
	max: $.validator.format("請輸入不大於 {0} 的數值"),
	min: $.validator.format("請輸入不小於 {0} 的數值")
});

}));