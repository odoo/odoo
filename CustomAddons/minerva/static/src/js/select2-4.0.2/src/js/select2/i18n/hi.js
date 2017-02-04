define(function () {
  // Hindi
  return {
    errorLoading: function () {
      return 'परिणामों को लोड नहीं किया जा सका।';
    },
    inputTooLong: function (args) {
      var overChars = args.input.length - args.maximum;

      var message =  overChars + ' अक्षर को हटा दें';

      if (overChars > 1) {
        message = overChars + ' अक्षरों को हटा दें ';
      }

      return message;
    },
    inputTooShort: function (args) {
      var remainingChars = args.minimum - args.input.length;

      var message = 'कृपया ' + remainingChars + ' या अधिक अक्षर दर्ज करें';

      return message;
    },
    loadingMore: function () {
      return 'अधिक परिणाम लोड हो रहे है...';
    },
    maximumSelected: function (args) {
      var message = 'आप केवल ' + args.maximum + ' आइटम का चयन कर सकते हैं';
      return message;
    },
    noResults: function () {
      return 'कोई परिणाम नहीं मिला';
    },
    searching: function () {
      return 'खोज रहा है...';
    }
  };
});
