define(function () {
  // Polish
  var charsWords = ['znak', 'znaki', 'znaków'];
  var itemsWords = ['element', 'elementy', 'elementów'];

  var pluralWord = function pluralWord(numberOfChars, words) {
    if (numberOfChars === 1) {
        return words[0];
    } else if (numberOfChars > 1 && numberOfChars <= 4) {
      return words[1];
    } else if (numberOfChars >= 5) {
      return words[2];
    }
  };
  
  return {
    errorLoading: function () {
      return 'Nie można załadować wyników.';
    },
    inputTooLong: function (args) {
      var overChars = args.input.length - args.maximum;

      return 'Usuń ' + overChars + ' ' + pluralWord(overChars, charsWords);
    },
    inputTooShort: function (args) {
      var remainingChars = args.minimum - args.input.length;
      
      return 'Podaj przynajmniej ' + remainingChars + ' ' +
        pluralWord(remainingChars, charsWords);
    },
    loadingMore: function () {
      return 'Trwa ładowanie…';
    },
    maximumSelected: function (args) {
      return 'Możesz zaznaczyć tylko ' + args.maximum + ' ' +
        pluralWord(args.maximum, itemsWords);
    },
    noResults: function () {
      return 'Brak wyników';
    },
    searching: function () {
      return 'Trwa wyszukiwanie…';
    }
  };
});
