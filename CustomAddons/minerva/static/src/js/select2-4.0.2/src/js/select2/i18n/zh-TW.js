define(function () {
  // Chinese (Traditional)
  return {
    inputTooLong: function (args) {
      var overChars = args.input.length - args.maximum;

      var message = '請刪掉' + overChars + '個字元';

      return message;
    },
    inputTooShort: function (args) {
      var remainingChars = args.minimum - args.input.length;

      var message = '請再輸入' + remainingChars + '個字元';

      return message;
    },
    loadingMore: function () {
      return '載入中…';
    },
    maximumSelected: function (args) {
      var message = '你只能選擇最多' + args.maximum + '項';

      return message;
    },
    noResults: function () {
      return '沒有找到相符的項目';
    },
    searching: function () {
      return '搜尋中…';
    }
  };
});
