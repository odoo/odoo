/**
 * Helper methods to work with dandelion datatables.
 */
(function (Dandelion, $) {

    /**
     * Label for various values with a custom class.
     */
    Dandelion.label = function (text, labelClass) {
        return '<span class="label label-sm ' + labelClass + '">' + text + '</span>';
    };

    /**
     * Label for nullable values.
     */
    Dandelion.nullLabel = function (data) {
        return data !== null ? data : Dandelion.label('N/A', 'label-danger');
    };

    /**
     * Helper method to convert string boolean to literal.
     */
    Dandelion.booleanValue = function (value, isTrue, isFalse) {
        return value == true ? isTrue : isFalse;
    };

    /**
     * Label which converts true to yes and false to no with some coloring.
     */
    Dandelion.yesNoLabel = function (data) {
        return data ? Dandelion.label('Yes', 'label-success') : Dandelion.label('No', 'label-danger');
    };

    /**
     * Format data to date.
     */

    Dandelion.date = function (data) {
        if (data) {
            var d = new Date(data);
            return $.datepicker.formatDate('yy.mm.dd ', d) + d.toTimeString().split(' ')[0];
        }
        return Dandelion.nullLabel(null);
    };

    /**
     * Action button for a table row.
     */
    Dandelion.actionButton = function (text, buttonClass, full) {
        return '<a href="javascript:;" class="btn default btn-xs ' + buttonClass + '" data-id="' + full.id + '">' + text + '</a>';
    };

    /**
     * Action button for element with a specified id.
     */
    Dandelion.actionButtonSpecific = function (text, buttonClass, id) {
        return '<a href="javascript:;" class="btn default btn-xs ' + buttonClass + '" data-id="' + id + '">' + text + '</a>';
    };

    /**
     * Add working scroll to the supplied table.
     */
    Dandelion.scrollFix = function(tableSelector) {
        $(function () {
            var table = $(tableSelector);

            //table.css({ margin: '0 !important', border: 0});
            table.wrap('<div style="overflow-x: auto"></div>');
        });
    };

    /**
     * Action button for element with a specified id and additional attribute.
     */
    Dandelion.actionButtonSpecific = function (text, buttonClass, id, attr) {
        return '<a href="javascript:;" class="btn default btn-xs ' + buttonClass +
            '" data-id="' + id +
            '" ' + attr + '>' +
            text + '</a>';
    };

    /**
     * href with custom attributes.
     */
    Dandelion.url = function url(url, text, attr) {
        return '<a href="' + url + '" ' + attr + '>' + text + '</a>';
    };

    /**
     * Simple href with a url and a class attribute.
     */
    Dandelion.urlButton = function urlButton(url, text, clazz) {
        return '<a href="' + url + '" class="btn default btn-xs ' + clazz + '">' + text + '</a>';
    };

    /**
     * Reload selected datatable.
     *
     * @param data array or a single table jQuery selector.
     */
    Dandelion.reload = function reload(data) {
        if (data instanceof Array) {
            $.each(data, function (i, obj) {
                $(obj).trigger('click');
            });
        } else {
            $(data).trigger('click');
        }
    };

    /**
     * Reload datatable while keeping pagination. Note that this must be included after datatables scripts are loaded.
     * Use <pre>&ltth:block ddl:placeholder-include="js"/></pre>
     *
     * @param selector datatable jQuery selector.
     */
    Dandelion.reloader = function reloader(selector) {
        $(selector).DataTable().ajax.reload(null, false);
    };

    /**
     * Label to be used on strings that can be null or empty. When null - a null label is shown, when empty an according
     * label is shown.
     */
    Dandelion.emptyLabel = function emptyLabel(data) {
        if (data == null) {
            return Dandelion.label('N/A', 'label-danger');
        } else if (data === "") {
            return Dandelion.label('Empty', 'label-primary');
        } else {
            return data;
        }
    }
}(window.Dandelion = window.Dandelion || {}, jQuery));