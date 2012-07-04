$(document).ready(function () {
    var $fix = $('#qunit-fixture');

    var instance;
    var baseSetup = function () {
        instance = openerp.testing.instanceFor('list_editable');

        openerp.testing.loadTemplate(instance);

        openerp.testing.mockifyRPC(instance);
    };
    module('editor', {
        setup: baseSetup
    });
    asyncTest('base-state', 2, function () {
        var e = new instance.web.list.Editor({
            dataset: {},
            editionView: function () {
                return {
                    arch: {
                        tag: 'form',
                        attrs: {
                            version: '7.0',
                            'class': 'oe_form_container'
                        },
                        children: []
                    }
                };
            }
        });
        e.appendTo($fix)
            .always(start)
            .fail(function (error) { ok(false, error && error.message); })
            .done(function () {
                ok(!e.isEditing(), "should not be editing");
                ok(e.form instanceof instance.web.FormView,
                   "should use default form type");
            });
    });
    asyncTest('toggle-edition-new', function () {
        instance.connection.responses['/web/dataset/call_kw:create'] = function () {
            return { result: 42 };
    };
        instance.connection.responses['/web/dataset/call_kw:read'] = function () {
            return { result: [{
                id: 42,
                a: false,
                b: false,
                c: false
            }]};
        };
        var e = new instance.web.list.Editor({
            do_warn: function (e) {
                warning = e;
            },
            dataset: new instance.web.DataSetSearch(),
            isPrependOnCreate: function () { return false; },
            editionView: function () {
                return {
                    arch: {
                        tag: 'form',
                        attrs: {
                            version: '7.0',
                            'class': 'oe_form_container'
                        },
                        children: [
                            {tag: 'field', attrs: {name: 'a'}},
                            {tag: 'field', attrs: {name: 'b'}},
                            {tag: 'field', attrs: {name: 'c'}}
                        ]
                    },
                    fields: {
                        a: {type: 'char'},
                        b: {type: 'char'},
                        c: {type: 'char'}
                    }
                };
            }
        });
        var counter = 0;
        var warning = null;
        e.appendTo($fix)
            .pipe(function () {
                return e.edit(null, function () {
                    ++counter;
                });
            })
            .pipe(function (form) {
                ok(e.isEditing(), "editor is now editing");
                equal(counter, 3, "all fields have been configured");
                strictEqual(form, e.form);
                return e.save();
            })
            .always(start)
            .fail(function (error) { ok(false, error && error.message); })
            .done(function (record) {
                ok(!warning, "should have received no warning");
                ok(!e.isEditing(), "should have stopped editing");
                equal(record.id, 42, "should have newly created id");
            })
    });
});
