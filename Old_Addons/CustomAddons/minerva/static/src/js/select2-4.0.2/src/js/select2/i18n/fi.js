define(function () {
  // Finnish
  return {
    inputTooLong: function (args) {
      var overChars = args.input.length - args.maximum;

      return 'Ole hyvä ja anna ' + overChars + ' merkkiä vähemmän';
    },
    inputTooShort: function (args) {
      var remainingChars = args.minimum - args.input.length;

      return 'Ole hyvä ja anna ' + remainingChars + ' merkkiä lisää';
    },
    loadingMore: function () {
      return 'Ladataan lisää tuloksia…';
    },
    maximumSelected: function (args) {
      return 'Voit valita ainoastaan ' + args.maximum + ' kpl';
    },
    noResults: function () {
      return 'Ei tuloksia';
    },
    searching: function () {

    }
  };
});
