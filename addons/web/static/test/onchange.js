$(document).ready(function () {
    var openerp,
        make_form = function (default_values) {
            var fields = {};
            _(default_values).each(function (value, name) {
                fields[name] = value instanceof Function ? value : {
                        get_on_change_value: function () { return value; }
                    };
            });
            return _.extend(new openerp.web.FormView(null, {}),
                    {fields: fields});
        };
    module("form.onchange", {
        setup: function () {
            openerp = window.openerp.init(true);
            window.openerp.web.core(openerp);
            window.openerp.web.chrome(openerp);
            // views loader stuff
            window.openerp.web.data(openerp);
            window.openerp.web.views(openerp);
            window.openerp.web.list(openerp);
            window.openerp.web.form(openerp);
        }
    });
    test('Parse args-less onchange', function () {
        var f = new openerp.web.FormView(null, {});
        var result = f.parse_on_change('on_change_foo()', {});
        equal(result.method, 'on_change_foo');
        deepEqual(result.args, []);
    });
    test('Parse 1-arg onchange', function () {
        var f = make_form({foo:  3});
        var result = f.parse_on_change('on_change_foo(foo)', {});
        equal(result.method, 'on_change_foo');
        deepEqual(result.args, [3]);
    });
    test('Parse 2-args onchange', function () {
        var f = make_form({foo: 3, bar: 'qux'});
        var result = f.parse_on_change('on_change_foo(bar, foo)', {});
        equal(result.method, 'on_change_foo');
        deepEqual(result.args, ['qux', 3]);
    });
    test('Literal null', function () {
        var f = make_form();
        var result = f.parse_on_change('on_null(None)', {});
        deepEqual(result.args, [null]);
    });
    test('Literal true', function () {
        var f = make_form();
        var result = f.parse_on_change('on_null(True)', {});
        deepEqual(result.args, [true]);
    });
    test('Literal false', function () {
        var f = make_form();
        var result = f.parse_on_change('on_null(False)', {});
        deepEqual(result.args, [false]);
    });
    test('Literal string', function () {
        var f = make_form();
        var result = f.parse_on_change('on_str("foo")', {});
        deepEqual(result.args, ['foo']);
        var result2 = f.parse_on_change("on_str('foo')", {});
        deepEqual(result2.args, ['foo']);
    });
    test('Literal number', function () {
        var f = make_form();
        var result = f.parse_on_change('on_str(42)', {});
        deepEqual(result.args, [42]);
        var result2 = f.parse_on_change("on_str(-25)", {});
        deepEqual(result2.args, [-25]);
        var result3 = f.parse_on_change("on_str(25.02)", {});
        deepEqual(result3.args, [25.02]);
    });
});
