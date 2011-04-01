$(document).ready(function () {
    var openerp;
    function get_widget(attrs) {
        var widget = new openerp.base.search.DateField(
                {attrs: attrs}, {name: 'foo'}, {inputs: []});
        $('#qunit-fixture').html(widget.render({}));
        widget.start();
        return widget;
    }

    module('search-date', {
        setup: function () {
            openerp = window.openerp.init(true);
            window.openerp.base.chrome(openerp);
            window.openerp.base.views(openerp);
            window.openerp.base.search(openerp);
        }
    });
    test('no values', function () {
        var widget = get_widget();
        deepEqual(widget.get_values(), {});
        strictEqual(widget.get_context(), null);
        strictEqual(widget.get_domain(), null);
    });
    test('filled from', function () {
        var widget = get_widget();
        widget.$element.find('input:eq(0)').val('1912-06-23');

        deepEqual(widget.get_values(), {from: '1912-06-23'});
        strictEqual(widget.get_context(), null);
        deepEqual(widget.get_domain(), [['foo', '>=', '1912-06-23']]);
    });
    test('filled to', function () {
        var widget = get_widget();
        widget.$element.find('input:eq(1)').val('1954-06-07');

        deepEqual(widget.get_values(), {to: '1954-06-07'});
        strictEqual(widget.get_context(), null);
        deepEqual(widget.get_domain(), [['foo', '<=', '1954-06-07']]);
    });
    test('filled both', function () {
        var widget = get_widget();
        widget.$element.find('input:eq(0)').val('1912-06-23');
        widget.$element.find('input:eq(1)').val('1954-06-07');

        deepEqual(widget.get_values(), {from: '1912-06-23', to: '1954-06-07'});
        strictEqual(widget.get_context(), null);
        deepEqual(widget.get_domain(),
                [['foo', '>=', '1912-06-23'], ['foo', '<=', '1954-06-07']]);
    });
    test('custom context', function () {
        var widget = get_widget({context: {__id: -1}});
        widget.$element.find('input:eq(0)').val('1912-06-23');
        widget.$element.find('input:eq(1)').val('1954-06-07');

        deepEqual(
            widget.get_context(),
            {__id: -1,
            own_values: {
                self: {from: '1912-06-23', to: '1954-06-07'}}});
    });
    test('custom filter_domain', function () {
        var widget = get_widget({filter_domain: {__id: -42}});
        widget.$element.find('input:eq(0)').val('1912-06-23');
        widget.$element.find('input:eq(1)').val('1954-06-07');

        deepEqual(
            widget.get_domain(),
            {__id: -42,
            own_values: {
                self: {from: '1912-06-23', to: '1954-06-07'}}});
    });
});
