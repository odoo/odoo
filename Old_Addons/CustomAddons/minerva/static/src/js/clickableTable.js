/**
 * jQuery plugin to make table rows selectable. Can be reused on any table.
 */
(function ($) {
    /**
     * Make selected table rows selectable.
     * @param callback after clicking a table row.
     */
    $.fn.clickableTable = function (callback) {
        var table = $(this);

        table.find('tbody').on('click', 'td', function (e) {
            var selection = getSelection().toString();
            if ($(e.target).is('a') || selection) {
                return e;
            } else {
                $(this).closest('tr').toggleClass('active');
                var ids = [];
                table.find('tr.active').each(function (i, obj) {
                    var id = $(obj).data('id');

                    // Check dandelion datatables variant (first column is the id).
                    if (id == null) {
                        id = Number($(obj).find('td:eq(0)').text());
                    }
                    ids[i] = id;
                });
                // Callback returns list of ids, of rows that were clicked.
                // Make sure that each row has attribute 'data-id' or this wont work.
                typeof callback === 'function' && callback(ids);
            }
        });
    };
}(jQuery));