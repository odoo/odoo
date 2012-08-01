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
            edition_view: function () {
                return makeFormView();
            }
        });
        e.appendTo($fix)
            .always(start)
            .fail(function (error) { ok(false, error && error.message); })
            .done(function () {
                ok(!e.is_editing(), "should not be editing");
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
            prepends_on_create: function () { return false; },
            edition_view: function () {
                return makeFormView([ field('a'), field('b'), field('c') ]);
            }
        });
        var counter = 0;
        e.appendTo($fix)
            .pipe(function () {
                return e.edit({}, function () {
                    ++counter;
                });
            })
            .pipe(function (form) {
                ok(e.is_editing(), "should be editing");
                equal(counter, 3, "should have configured all fields");
                return e.save();
            })
            .always(start)
            .fail(function (error) { ok(false, error && error.message); })
            .done(function (record) {
                ok(!e.is_editing(), "should have stopped editing");
                equal(record.id, 42, "should have newly created id");
            })
    });
    asyncTest('toggle-edition-cancel', 2, function () {
        instance.connection.responses['/web/dataset/call_kw:create'] = function () {
            return { result: 42 };
        };
        var e = new instance.web.list.Editor({
            dataset: new instance.web.DataSetSearch(),
            prepends_on_create: function () { return false; },
            edition_view: function () {
                return makeFormView([ field('a'), field('b'), field('c') ]);
            }
        });
        var counter = 0;
        e.appendTo($fix)
            .pipe(function () {
                return e.edit({}, function () {
                    ++counter;
                });
            })
            .pipe(function (form) {
                return e.cancel();
            })
            .always(start)
            .fail(function (error) { ok(false, error && error.message); })
            .done(function (record) {
                ok(!e.is_editing(), "should have stopped editing");
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
            prepends_on_create: function () { return false; },
            edition_view: function () {
                return makeFormView([
                    field('a', {required: true}), field('b'), field('c') ]);
            }
        });
        var counter = 0;
        var warnings = 0;
        e.appendTo($fix)
            .pipe(function () {
                return e.edit({}, function () {
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
                ok(e.is_editing(), "should have kept editing");
            })
    });

    module('list-edition', {
        setup: function () {
            baseSetup();

            var records = {};
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
                },
                '/web/dataset/call_kw:create': function (params) {
                    records[42] = _.extend({}, params.params.args[0]);
                    return {result: 42};
                },
                '/web/dataset/call_kw:read': function (params) {
                    var id = params.params.args[0][0];
                    if (id in records) {
                        return {result: [records[id]]};
                    }
                    return {result: []};
                }
            })
        }
    });
    asyncTest('newrecord', 6, function () {
        var got_defaults = false;
        instance.connection.responses['/web/dataset/call_kw:default_get'] = function (params) {
            var fields = params.params.args[0];
            deepEqual(
                fields, ['a', 'b', 'c'],
                "should ask defaults for all fields");
            got_defaults = true;
            return {result: {
                a: "qux",
                b: "quux"
            }};
        };

        var ds = new instance.web.DataSetStatic(null, 'demo', null, [1]);
        var l = new instance.web.ListView({}, ds, false, {editable: 'top'});

        l.appendTo($fix)
            .pipe(l.proxy('reload_content'))
            .pipe(function () {
                return l.start_edition();
            })
            .always(start)
            .pipe(function () {
                ok(got_defaults, "should have fetched default values for form");
                return l.save_edition();
            })
            .pipe(function (result) {
                ok(result.created, "should yield newly created record");
                equal(result.record.get('a'), "qux",
                      "should have used default values");
                equal(result.record.get('b'), "quux",
                      "should have used default values");
                ok(!result.record.get('c'),
                    "should have no value if there was no default");
            })
            .fail(function (e) { ok(false, e && e.message || e); });
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
                },
                '/web/dataset/call_kw:read': function (params) {
                    return {result: [{
                        id: 1,
                        a: 'foo',
                        b: 'bar',
                        c: 'baz'
                    }]};
                }
            });
        }
    });
    asyncTest('edition events', 4, function () {
        var ds = new instance.web.DataSetStatic(null, 'demo', null, [1]);
        var o = {
            counter: 0,
            onEvent: function (e) { this.counter++; }
        };
        var l = new instance.web.ListView({}, ds, false, {editable: 'top'});
        l.on('edit:before edit:after', o, o.onEvent);
        l.appendTo($fix)
            .pipe(l.proxy('reload_content'))
            .always(start)
            .pipe(function () {
                ok(l.options.editable, "should be editable");
                equal(o.counter, 0, "should have seen no event yet");
                return l.start_edition(l.records.get(1));
            })
            .pipe(function () {
                ok(l.editor.is_editing(), "should be editing");
                equal(o.counter, 2, "should have seen two edition events");
            })
            .fail(function (e) { ok(false, e && e.message); });
    });

    asyncTest('edition events: cancelling', 3, function () {
        var edit_after = false;
        var ds = new instance.web.DataSetStatic(null, 'demo', null, [1]);
        var l = new instance.web.ListView({}, ds, false, {editable: 'top'});
        l.on('edit:before', {}, function (e) {
            e.cancel = true;
        });
        l.on('edit:after', {}, function () {
            edit_after = true;
        });
        l.appendTo($fix)
            .pipe(l.proxy('reload_content'))
            .always(start)
            .pipe(function () {
                ok(l.options.editable, "should be editable");
                return l.start_edition();
            })
            // cancelling an event rejects the deferred
            .pipe($.Deferred().reject(), function () {
                ok(!l.editor.is_editing(), "should not be editing");
                ok(!edit_after, "should not have fired the edit:after event");
                return $.when();
            })
            .fail(function (e) { ok(false, e && e.message || e); });
    });
});
