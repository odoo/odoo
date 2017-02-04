define(function () {
  // Slovak

  // use text for the numbers 2 through 4
  var smallNumbers = {
    2: function (masc) { return (masc ? 'dva' : 'dve'); },
    3: function () { return 'tri'; },
    4: function () { return 'štyri'; }
  };

  return {
    inputTooLong: function (args) {
      var overChars = args.input.length - args.maximum;

      if (overChars == 1) {
        return 'Prosím, zadajte o jeden znak menej';
      } else if (overChars >= 2 && overChars <= 4) {
        return 'Prosím, zadajte o ' + smallNumbers[overChars](true) +
          ' znaky menej';
      } else {
        return 'Prosím, zadajte o ' + overChars + ' znakov menej';
      }
    },
    inputTooShort: function (args) {
      var remainingChars = args.minimum - args.input.length;

      if (remainingChars == 1) {
        return 'Prosím, zadajte ešte jeden znak';
      } else if (remainingChars <= 4) {
        return 'Prosím, zadajte ešte ďalšie ' +
          smallNumbers[remainingChars](true) + ' znaky';
      } else {
        return 'Prosím, zadajte ešte ďalších ' + remainingChars + ' znakov';
      }
    },
    loadingMore: function () {
      return 'Loading more results…';
    },
    maximumSelected: function (args) {
      if (args.maximum == 1) {
        return 'Môžete zvoliť len jednu položku';
      } else if (args.maximum >= 2 && args.maximum <= 4) {
        return 'Môžete zvoliť najviac ' + smallNumbers[args.maximum](false) +
          ' položky';
      } else {
        return 'Môžete zvoliť najviac ' + args.maximum + ' položiek';
      }
    },
    noResults: function () {
      return 'Nenašli sa žiadne položky';
    },
    searching: function () {
      return 'Vyhľadávanie…';
    }
  };
});
