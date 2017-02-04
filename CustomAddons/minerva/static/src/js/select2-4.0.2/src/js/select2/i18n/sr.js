define(function () {
  // Serbian
  function ending (count, one, some, many) {
    if (count % 10 == 1 && count % 100 != 11) {
      return one;
    }

    if (count % 10 >= 2 && count % 10 <= 4 &&
      (count % 100 < 12 || count % 100 > 14)) {
        return some;
    }

    return many;
  }

  return {
    errorLoading: function () {
      return 'Preuzimanje nije uspelo.';
    },
    inputTooLong: function (args) {
      var overChars = args.input.length - args.maximum;

      var message = 'Obrišite ' + overChars + ' simbol';

      message += ending(overChars, '', 'a', 'a');

      return message;
    },
    inputTooShort: function (args) {
      var remainingChars = args.minimum - args.input.length;

      var message = 'Ukucajte bar još ' + remainingChars + ' simbol';

      message += ending(remainingChars, '', 'a', 'a');

      return message;
    },
    loadingMore: function () {
      return 'Preuzimanje još rezultata…';
    },
    maximumSelected: function (args) {
      var message = 'Možete izabrati samo ' + args.maximum + ' stavk';

      message += ending(args.maximum, 'u', 'e', 'i');

      return message;
    },
    noResults: function () {
      return 'Ništa nije pronađeno';
    },
    searching: function () {
      return 'Pretraga…';
    }
  };
});
