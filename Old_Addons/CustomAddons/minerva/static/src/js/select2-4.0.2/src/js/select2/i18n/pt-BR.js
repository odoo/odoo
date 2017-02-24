define(function () {
  // Brazilian Portuguese
  return {
    errorLoading: function () {
      return 'Os resultados não puderam ser carregados.';
    },
    inputTooLong: function (args) {
      var overChars = args.input.length - args.maximum;

      var message = 'Apague ' + overChars + ' caracter';

      if (overChars != 1) {
        message += 'es';
      }

      return message;
    },
    inputTooShort: function (args) {
      var remainingChars = args.minimum - args.input.length;

      var message = 'Digite ' + remainingChars + ' ou mais caracteres';

      return message;
    },
    loadingMore: function () {
      return 'Carregando mais resultados…';
    },
    maximumSelected: function (args) {
      var message = 'Você só pode selecionar ' + args.maximum + ' ite';

      if (args.maximum == 1) {
        message += 'm';
      } else {
        message += 'ns';
      }

      return message;
    },
    noResults: function () {
      return 'Nenhum resultado encontrado';
    },
    searching: function () {
      return 'Buscando…';
    }
  };
});
