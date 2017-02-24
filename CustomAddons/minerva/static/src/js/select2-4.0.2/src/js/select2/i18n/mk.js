define(function () {
  // Macedonian
  return {
    inputTooLong: function (args) {
      var overChars = args.input.length - args.maximum;

      var message = 'Ве молиме внесете ' + args.maximum + ' помалку карактер';

      if (args.maximum !== 1) {
        message += 'и';
      }

      return message;
    },
    inputTooShort: function (args) {
      var remainingChars = args.minimum - args.input.length;

      var message = 'Ве молиме внесете уште ' + args.maximum + ' карактер';

      if (args.maximum !== 1) {
        message += 'и';
      }

      return message;
    },
    loadingMore: function () {
      return 'Вчитување резултати…';
    },
    maximumSelected: function (args) {
      var message = 'Можете да изберете само ' + args.maximum + ' ставк';

      if (args.maximum === 1) {
        message += 'а';
      } else {
        message += 'и';
      }

      return message;
    },
    noResults: function () {
      return 'Нема пронајдено совпаѓања';
    },
    searching: function () {
      return 'Пребарување…';
    }
  };
});
