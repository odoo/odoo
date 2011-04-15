$(document).ready(function () {
    /**
     * Tests a jQuery collection against a selector ("ands" the .is() of each
     * member of the collection, instead of "or"-ing them)
     *
     * @param {jQuery} $c a jQuery collection object
     * @param {String} selector the selector to test the collection against
     */
    var are = function ($c, selector) {
        return ($c.filter(function () { return $(this).is(selector); }).length
                === $c.length);
    };

    var fvg = {fields_view: {
        'fields': [],
        'arch': {
            'attrs': {string: ''}
        }
    }};

    var openerp;
    module("ListView", {
        setup: function () {
            openerp = window.openerp.init(true);
            window.openerp.base.chrome(openerp);
            // views loader stuff
            window.openerp.base.data(openerp);
            window.openerp.base.views(openerp);
            window.openerp.base.form(openerp);
            window.openerp.base.list(openerp);
        }
    });

    asyncTest('render selection checkboxes', 2, function () {
        var listview = new openerp.base.ListView(
                {}, null,
                'qunit-fixture', {model: null});

        listview.on_loaded(fvg);

        listview.do_fill_table([
                {data: {id: {value: null}}},
                {data: {id: {value: null}}},
                {data: {id: {value: null}}}
        ]).then(function () {
            ok(are(listview.$element.find('tbody th'),
                   '.oe-record-selector'));
            ok(are(listview.$element.find('tbody th input'),
                   ':checkbox:not([name])'));
            start();
        });
    });
    asyncTest('render no checkbox if selectable=false', 1, function () {
        var listview = new openerp.base.ListView(
                {}, null,
                'qunit-fixture', {model: null}, false,
                {selectable: false});

        listview.on_loaded(fvg);

        listview.do_fill_table([
                {data: {id: {value: null}}},
                {data: {id: {value: null}}},
                {data: {id: {value: null}}}
        ]).then(function () {
            equal(listview.$element.find('tbody th').length, 0);
            start();
        });
    });
    asyncTest('select a bunch of records', 2, function () {
        var listview = new openerp.base.ListView(
                {}, null, 'qunit-fixture', {model: null});
        listview.on_loaded(fvg);

        listview.do_fill_table([
                {data: {id: {value: 1}}},
                {data: {id: {value: 2}}},
                {data: {id: {value: 3}}}
        ]).then(function () {
            listview.$element.find('tbody th input:eq(2)')
                             .attr('checked', true);
            deepEqual(listview.get_selection(), [3]);
            listview.$element.find('tbody th input:eq(1)')
                             .attr('checked', true);
            deepEqual(listview.get_selection(), [2, 3]);
            start();
        });
    });
    asyncTest('render deletion button if list is deletable', 1, function () {
        var listview = new openerp.base.ListView(
                {}, null, 'qunit-fixture', {model: null});

        listview.on_loaded(fvg);

        listview.do_fill_table([
                {data: {id: {value: null}}},
                {data: {id: {value: null}}},
                {data: {id: {value: null}}}
        ]).then(function () {
            equal(
                listview.$element.find('tbody tr td.oe-record-delete button').length,
                3);
            start();
        });
    });
    asyncTest('deletion button should lead on deletion in the dataset',
              2, function () {
        var deleted;
        var listview = new openerp.base.ListView(
                {}, null, 'qunit-fixture', {model: null, unlink: function (ids) {
            deleted = ids;
        }});

        listview.on_loaded(fvg);

        listview.do_fill_table([
                {data: {id: {value: 1}}},
                {data: {id: {value: 2}}},
                {data: {id: {value: 3}}}
        ]).then(function () {
            listview.$element.find('tbody td.oe-record-delete:eq(2) button').click();
            deepEqual(deleted, [3]);
            listview.$element.find('tbody td.oe-record-delete:eq(0) button').click();
            deepEqual(deleted, [1]);
            start();
        });
    });
    asyncTest('multiple records deletion', 1, function () {
        var deleted;
        var listview = new openerp.base.ListView(
                {}, null, 'qunit-fixture', {model: null, unlink: function (ids) {
            deleted = ids;
        }});

        listview.on_loaded(fvg);

        listview.do_fill_table([
                {data: {id: {value: 1}}},
                {data: {id: {value: 2}}},
                {data: {id: {value: 3}}}
        ]).then(function () {
            listview.$element.find('tbody th input:eq(2)')
                             .attr('checked', true);
            listview.$element.find('tbody th input:eq(1)')
                             .attr('checked', true);

            listview.$element.find('#oe-list-delete').click();
            deepEqual(deleted, [2, 3]);
            start();
        });
    });
});
