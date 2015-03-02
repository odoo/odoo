/**
 * Select2 Polish translation.
 *
 * @author  Jan Kondratowicz <jan@kondratowicz.pl>
 * @author  Uriy Efremochkin <efremochkin@uriy.me>
 * @author  Michał Połtyn <mike@poltyn.com>
 * @author  Damian Zajkowski <damian.zajkowski@gmail.com>
 */
(function($) {
    "use strict";

    $.fn.select2.locales['pl'] = {
        formatNoMatches: function() {
            return "Brak wyników";
        },
        formatInputTooShort: function(input, min) {
            return "Wpisz co najmniej" + character(min - input.length, "znak", "i");
        },
        formatInputTooLong: function(input, max) {
            return "Wpisana fraza jest za długa o" + character(input.length - max, "znak", "i");
        },
        formatSelectionTooBig: function(limit) {
            return "Możesz zaznaczyć najwyżej" + character(limit, "element", "y");
        },
        formatLoadMore: function(pageNumber) {
            return "Ładowanie wyników…";
        },
        formatSearching: function() {
            return "Szukanie…";
        }
    };

    $.extend($.fn.select2.defaults, $.fn.select2.locales['pl']);

    function character(n, word, pluralSuffix) {
        //Liczba pojedyncza - brak suffiksu
        //jeden znak
        //jeden element
        var suffix = '';
        if (n > 1 && n < 5) {
            //Liczaba mnoga ilość od 2 do 4 - własny suffiks
            //Dwa znaki, trzy znaki, cztery znaki.
            //Dwa elementy, trzy elementy, cztery elementy
            suffix = pluralSuffix;
        } else if (n == 0 || n >= 5) {
            //Ilość 0 suffiks ów
            //Liczaba mnoga w ilości 5 i więcej - suffiks ów (nie poprawny dla wszystkich wyrazów, np. 100 wiadomości)
            //Zero znaków, Pięć znaków, sześć znaków, siedem znaków, osiem znaków.
            //Zero elementów Pięć elementów, sześć elementów, siedem elementów, osiem elementów.
            suffix = 'ów';
        }
        return " " + n + " " + word + suffix;
    }
})(jQuery);
