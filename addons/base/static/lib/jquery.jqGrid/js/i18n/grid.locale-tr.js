;(function($){
/**
 * jqGrid Turkish Translation
 * Erhan Gündoğan (erhan@trposta.net)
 * http://blog.zakkum.com
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
$.jgrid = {
	defaults : {
		recordtext: "{0}-{1} listeleniyor. Toplam:{2}",
	    emptyrecords: "Kayıt bulunamadı",
		loadtext: "Yükleniyor...",
		pgtext : "{0}/{1}. Sayfa"
	},
	search : {
	    caption: "Arama...",
	    Find: "Bul",
	    Reset: "Temizle",	    
	    odata : ['eşit', 'eşit değil', 'daha az', 'daha az veya eşit', 'daha fazla', 'daha fazla veya eşit', 'ile başlayan', 'ile başlamayan', 'içinde', 'içinde değil', 'ile biten', 'ile bitmeyen', 'içeren', 'içermeyen'],
	    groupOps: [	{ op: "VE", text: "tüm" },	{ op: "VEYA",  text: "herhangi" }	],
		matchText: " uyan",
		rulesText: " kurallar"
	},
	edit : {
	    addCaption: "Kayıt Ekle",
	    editCaption: "Kayıt Düzenle",
	    bSubmit: "Gönder",
	    bCancel: "İptal",
		bClose: "Kapat",
		saveData: "Veriler değişti! Kayıt edilsin mi?",
		bYes : "Evet",
		bNo : "Hayıt",
		bExit : "İptal",
	    msg: {
	        required:"Alan gerekli",
	        number:"Lütfen bir numara giriniz",
	        minValue:"girilen değer daha büyük ya da buna eşit olmalıdır",
	        maxValue:"girilen değer daha küçük ya da buna eşit olmalıdır",
	        email: "geçerli bir e-posta adresi değildir",
	        integer: "Lütfen bir tamsayı giriniz",
			url: "Geçerli bir URL değil. ('http://' or 'https://') ön eki gerekli.",
			nodefined : " is not defined!",
			novalue : " return value is required!",
			customarray : "Custom function should return array!",
			customfcheck : "Custom function should be present in case of custom checking!"
		}
	},
	view : {
	    caption: "Kayıt Görüntüle",
	    bClose: "Kapat"
	},
	del : {
	    caption: "Sil",
	    msg: "Seçilen kayıtlar silinsin mi?",
	    bSubmit: "Sil",
	    bCancel: "İptal"
	},
	nav : {
		edittext: " ",
	    edittitle: "Seçili satırı düzenle",
		addtext:" ",
	    addtitle: "Yeni satır ekle",
	    deltext: " ",
	    deltitle: "Seçili satırı sil",
	    searchtext: " ",
	    searchtitle: "Kayıtları bul",
	    refreshtext: "",
	    refreshtitle: "Tabloyu yenile",
	    alertcap: "Uyarı",
	    alerttext: "Lütfen bir satır seçiniz",
		viewtext: "",
		viewtitle: "Seçilen satırı görüntüle"
	},
	col : {
	    caption: "Sütunları göster/gizle",
	    bSubmit: "Gönder",
	    bCancel: "İptal"	
	},
	errors : {
		errcap : "Hata",
		nourl : "Bir url yapılandırılmamış",
		norecords: "İşlem yapılacak bir kayıt yok",
	    model : "colNames uzunluğu <> colModel!"
	},
	formatter : {
		integer : {thousandsSeparator: " ", defaultValue: '0'},
		number : {decimalSeparator:".", thousandsSeparator: " ", decimalPlaces: 2, defaultValue: '0.00'},
		currency : {decimalSeparator:".", thousandsSeparator: " ", decimalPlaces: 2, prefix: "", suffix:"", defaultValue: '0.00'},
		date : {
			dayNames:   [
				"Paz", "Pts", "Sal", "Çar", "Per", "Cum", "Cts",
				"Pazar", "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi"
			],
			monthNames: [
				"Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara",
				"Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
			],
			AmPm : ["am","pm","AM","PM"],
			S: function (j) {return j < 11 || j > 13 ? ['st', 'nd', 'rd', 'th'][Math.min((j - 1) % 10, 3)] : 'th'},
			srcformat: 'Y-m-d',
			newformat: 'd/m/Y',
			masks : {
	            ISO8601Long:"Y-m-d H:i:s",
	            ISO8601Short:"Y-m-d",
	            ShortDate: "n/j/Y",
	            LongDate: "l, F d, Y",
	            FullDateTime: "l, F d, Y g:i:s A",
	            MonthDay: "F d",
	            ShortTime: "g:i A",
	            LongTime: "g:i:s A",
	            SortableDateTime: "Y-m-d\\TH:i:s",
	            UniversalSortableDateTime: "Y-m-d H:i:sO",
	            YearMonth: "F, Y"
	        },
	        reformatAfterEdit : false
		},
		baseLinkUrl: '',
		showAction: '',
	    target: '',
	    checkbox : {disabled:true},
		idName : 'id'
	}
};
})(jQuery);
