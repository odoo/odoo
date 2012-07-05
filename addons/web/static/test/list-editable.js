$(document).ready(function () {
    var $fix = $('#qunit-fixture');

    var instance;
    var baseSetup = function () {
        instance = openerp.testing.instanceFor('list_editable');

        openerp.testing.loadTemplate(instance);

        openerp.testing.mockifyRPC(instance);
    };


    /**
     *
     * @param {String} name
     * @param {Object} [attrs]
     * @param {String} [attrs.type="char"]
     * @param {Boolean} [attrs.required]
     * @param {Boolean} [attrs.invisible]
     * @param {Boolean} [attrs.readonly]
     * @return {Object}
     */
    function field(name, attrs) {
        attrs = attrs || {};
        attrs.name = name;
        return _.defaults(attrs, {
            type: 'char'
        });
    }

    /**
     * @param {Array} fields
     * @return {Object}
     */
    function makeFormView(fields) {
        var fobj = {};
        _(fields).each(function (field) {
            fobj[field.name] = {
                type: field.type,
                string: field.string
            };
        });
        var children = _(fields).map(function (field) {
            return {
                tag: 'field',
                attrs: {
                    name: field.name,
                    modifiers: JSON.stringify({
                        required: field.required,
                        invisible: field.invisible,
                        readonly: field.readonly
                    })
                }
            }
        });
        return {
            arch: {
                tag: 'form',
                attrs: {
                    version: '7.0',
                    'class': 'oe_form_container'
                },
                children: children
            },
            fields: fobj
        };
    }

    module('editor', {
        setup: baseSetup
    });
    asyncTest('base-state', 2, function () {
        var e = new instance.web.list.Editor({
            dataset: {},
            editionView: function () {
                return makeFormView();
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
    asyncTest('toggle-edition-save', 4, function () {
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
            dataset: new instance.web.DataSetSearch(),
            isPrependOnCreate: function () { return false; },
            editionView: function () {
                return makeFormView([ field('a'), field('b'), field('c') ]);
            }
        });
        var counter = 0;
        e.appendTo($fix)
            .pipe(function () {
                return e.edit(null, function () {
                    ++counter;
                });
            })
            .pipe(function (form) {
                ok(e.isEditing(), "should be editing");
                equal(counter, 3, "should have configured all fields");
                return e.save();
            })
            .always(start)
            .fail(function (error) { ok(false, error && error.message); })
            .done(function (record) {
                ok(!e.isEditing(), "should have stopped editing");
                equal(record.id, 42, "should have newly created id");
            })
    });
    asyncTest('toggle-edition-cancel', 2, function () {
        instance.connection.responses['/web/dataset/call_kw:create'] = function () {
            return { result: 42 };
        };
        var e = new instance.web.list.Editor({
            dataset: new instance.web.DataSetSearch(),
            isPrependOnCreate: function () { return false; },
            editionView: function () {
                return makeFormView([ field('a'), field('b'), field('c') ]);
            }
        });
        var counter = 0;
        e.appendTo($fix)
            .pipe(function () {
                return e.edit(null, function () {
                    ++counter;
                });
            })
            .pipe(function (form) {
                return e.cancel();
            })
            .always(start)
            .fail(function (error) { ok(false, error && error.message); })
            .done(function (record) {
                ok(!e.isEditing(), "should have stopped editing");
                ok(!record.id, "should have no id");
            })
    });
    asyncTest('toggle-save-required', 2, function () {
        instance.connection.responses['/web/dataset/call_kw:create'] = function () {
            return { result: 42 };
        };
        var e = new instance.web.list.Editor({
            do_warn: function () {
                warnings++;
            },
            dataset: new instance.web.DataSetSearch(),
            isPrependOnCreate: function () { return false; },
            editionView: function () {
                return makeFormView([
                    field('a', {required: true}), field('b'), field('c') ]);
            }
        });
        var counter = 0;
        var warnings = 0;
        e.appendTo($fix)
            .pipe(function () {
                return e.edit(null, function () {
                    ++counter;
                });
            })
            .pipe(function (form) {
                return e.save();
            })
            .always(start)
            .done(function () { ok(false, "cancel should not succeed"); })
            .fail(function () {
                equal(warnings, 1, "should have been warned");
                ok(e.isEditing(), "should have kept editing");
            })
    });

    module('list-edition-events', {
        setup: function () {
            baseSetup();
            _.extend(instance.connection.responses, {
                '/web/listview/load': function () {
                    return {result: {
                        type: 'tree',
                        fields: {
                            a: {type: 'char', string: "A"},
                            b: {type: 'char', string: "B"},
                            c: {type: 'char', string: "C"}
                        },
                        arch: {
                            tag: 'tree',
                            attrs: {},
                            children: [
                                {tag: 'field', attrs: {name: 'a'}},
                                {tag: 'field', attrs: {name: 'b'}},
                                {tag: 'field', attrs: {name: 'c'}}
                            ]
                        }
                    }};
                }
            });
        }
    });
    asyncTest('edition events', function () {
        var ds = new instance.web.DataSetStatic(null, 'demo', null, [1]);
        var o = {
            counter: 0,
            onEvent: function (e) { this.counter++; }
        };
        var l = new instance.web.ListView(null, ds);
        l.set_editable(true);
        l.on('edit:before edit:after', o, o.onEvent);
        l.appendTo($fix)
            .always(start)
            .pipe(function () {
                ok(l.options.editable, "should be editable");
                equal(o.counter, 0, "should have seen no event yet");
                return l.startEdition();
            })
            .pipe(function () {
                ok(l.editor.isEditing(), "should be editing");
                equal(o.counter, 2, "should have seen two edition events");
            })
            .fail(function (e) { ok(false, e && e.message); });
    });
    // TODO: test cancelling edition events
});
