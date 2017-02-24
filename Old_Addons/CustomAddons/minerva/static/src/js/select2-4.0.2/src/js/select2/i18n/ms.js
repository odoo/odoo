define(function () {
  // Malay
  return {
    errorLoading: function () {
      return 'Keputusan tidak berjaya dimuatkan.';
    },
    inputTooLong: function (args) {
      var overChars = args.input.length - args.maximum;

      return 'Sila hapuskan ' + overChars + ' aksara';
    },
    inputTooShort: function (args) {
      var remainingChars = args.minimum - args.input.length;

      return 'Sila masukkan ' + remainingChars + ' atau lebih aksara';
    },
    loadingMore: function () {
      return 'Sedang memuatkan keputusan…';
    },
    maximumSelected: function (args) {
      return 'Anda hanya boleh memilih ' + args.maximum + ' pilihan';
    },
    noResults: function () {
      return 'Tiada padanan yang ditemui';
    },
    searching: function () {
      return 'Mencari…';
    }
  };
});