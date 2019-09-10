openerp.testing.section('editor', {
    dependencies: ['web.list_editable'],
    rpc: 'mock',
    templates: true,
    setup: function (instance, $s, mock) {
        mock('test.model:create', function () {
            return 42;
        });
        mock('test.model:onchange', function () {
            return {};
        });
    }
}, function (test) {
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
     * @param {Array} [fields]
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
            };
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

    test('base-state', {asserts: 2}, function (instance, $fix) {
        var e = new instance.web.list.Editor({
            dataset: {ids: []},
            edition_view: function () {
                return makeFormView();
            }
        });
        return e.appendTo($fix)
            .done(function () {
                ok(!e.is_editing(), "should not be editing");
                ok(e.form instanceof instance.web.FormView,
                   "should use default form type");
            });
    });
    test('toggle-edition-save', {
        asserts: 4,
        setup: function (instance, $s, mock) {
            mock('test.model:search_read', function () {
                return [{id: 42, a: false, b: false, c: false}];
            });
        }
    }, function (instance, $fix) {
        var e = new instance.web.list.Editor({
            dataset: new instance.web.DataSetSearch(null, 'test.model'),
            prepends_on_create: function () { return false; },
            edition_view: function () {
                return makeFormView([ field('a'), field('b'), field('c') ]);
            }
        });
        var counter = 0;
        return e.appendTo($fix)
            .then(function () {
                return e.edit({}, function () {
                    ++counter;
                });
            })
            .then(function (form) {
                ok(e.is_editing(), "should be editing");
                equal(counter, 3, "should have configured all fields");
                return e.save();
            })
            .done(function (record) {
                ok(!e.is_editing(), "should have stopped editing");
                equal(record.id, 42, "should have newly created id");
            });
    });
    test('toggle-edition-cancel', { asserts: 2 }, function (instance, $fix) {
        var e = new instance.web.list.Editor({
            dataset: new instance.web.DataSetSearch(null, 'test.model'),
            prepends_on_create: function () { return false; },
            edition_view: function () {
                return makeFormView([ field('a'), field('b'), field('c') ]);
            }
        });
        var counter = 0;
        return e.appendTo($fix)
            .then(function () {
                return e.edit({}, function () {
                    ++counter;
                });
            })
            .then(function (form) {
                return e.cancel();
            })
            .done(function (record) {
                ok(!e.is_editing(), "should have stopped editing");
                ok(!record.id, "should have no id");
            });
    });
    test('toggle-save-required', {
        asserts: 2,
        fail_on_rejection: false
    }, function (instance, $fix) {
        var e = new instance.web.list.Editor({
            do_warn: function () {
                warnings++;
            },
            dataset: new instance.web.DataSetSearch(null, 'test.model'),
            prepends_on_create: function () { return false; },
            edition_view: function () {
                return makeFormView([
                    field('a', {required: true}), field('b'), field('c') ]);
            }
        });
        var counter = 0;
        var warnings = 0;
        return e.appendTo($fix)
            .then(function () {
                return e.edit({}, function () {
                    ++counter;
                });
            })
            .then(function (form) {
                return e.save();
            })
            .done(function () { ok(false, "cancel should not succeed"); })
            .fail(function () {
                equal(warnings, 1, "should have been warned");
                ok(e.is_editing(), "should have kept editing");
            });
    });
});
openerp.testing.section('list.edition', {
    dependencies: ['web.list_editable'],
    rpc: 'mock',
    templates: true,
    setup: function (instance, $s, mock) {
        var records = {};
        mock('demo:create', function (args) {
            records[42] = _.extend({}, args[0]);
            return 42;
        });
        mock('demo:read', function (args) {
            var id = args[0][0];
            if (id in records) {
                return [records[id]];
            }
            return [];
        });
        mock('demo:search_read', function (args) {
            // args[0][0] = ["id", "=", 42] 
            // args[0][0] = 42
            var id = args[0][0][2];
            if (id in records) {
                return [records[id]];
            }
            return [];
        });
        mock('demo:fields_view_get', function () {
            return {
                type: 'tree',
                fields: {
                    a: {type: 'char', string: "A"},
                    b: {type: 'char', string: "B"},
                    c: {type: 'char', string: "C"}
                },
                arch: '<tree><field name="a"/><field name="b"/><field name="c"/></tree>',
            };
        });
        mock('demo:onchange', function () {
            return {};
        });
    }
}, function (test) {
    test('newrecord', {asserts: 6}, function (instance, $fix, mock) {
        var got_defaults = false;
        mock('demo:default_get', function (args) {
            var fields = args[0];
            deepEqual(
                fields, ['a', 'b', 'c'],
                "should ask defaults for all fields");
            got_defaults = true;
            return { a: "qux", b: "quux" };
        });

        var ds = new instance.web.DataSetStatic(null, 'demo', null, [1]);
        var l = new instance.web.ListView({}, ds, false, {editable: 'top'});

        return l.appendTo($fix)
            .then(l.proxy('reload_content'))
            .then(function () {
                return l.start_edition();
            })
            .then(function () {
                ok(got_defaults, "should have fetched default values for form");

                return l.save_edition();
            })
            .then(function (result) {
                ok(result.created, "should yield newly created record");
                equal(result.record.get('a'), "qux",
                      "should have used default values");
                equal(result.record.get('b'), "quux",
                      "should have used default values");
                ok(!result.record.get('c'),
                    "should have no value if there was no default");
            });
    });
});
openerp.testing.section('list.edition.events', {
    dependencies: ['web.list_editable'],
    rpc: 'mock',
    templates: true,
    setup: function (instance, $s, mock) {
        mock('demo:read', function () {
            return [{ id: 1, a: 'foo', b: 'bar', c: 'baz' }];
        });
        mock('demo:fields_view_get', function () {
            return {
                type: 'tree',
                fields: {
                    a: {type: 'char', string: "A"},
                    b: {type: 'char', string: "B"},
                    c: {type: 'char', string: "C"}
                },
                arch: '<tree><field name="a"/><field name="b"/><field name="c"/></tree>',
            };
        });
    }
}, function (test) {
    test('edition events', {asserts: 4}, function (instance, $fix) {
        var ds = new instance.web.DataSetStatic(null, 'demo', null, [1]);
        var o = {
            counter: 0,
            onEvent: function (e) { this.counter++; }
        };
        var l = new instance.web.ListView({}, ds, false, {editable: 'top'});
        l.on('edit:before edit:after', o, o.onEvent);
        return l.appendTo($fix)
            .then(l.proxy('reload_content'))
            .then(function () {
                ok(l.options.editable, "should be editable");
                equal(o.counter, 0, "should have seen no event yet");
                return l.start_edition(l.records.get(1));
            })
            .then(function () {
                ok(l.editor.is_editing(), "should be editing");
                equal(o.counter, 2, "should have seen two edition events");
            });
    });

    test('edition events: cancelling', {asserts: 3}, function (instance, $fix) {
        var edit_after = false;
        var ds = new instance.web.DataSetStatic(null, 'demo', null, [1]);
        var l = new instance.web.ListView({}, ds, false, {editable: 'top'});
        l.on('edit:before', {}, function (e) {
            e.cancel = true;
        });
        l.on('edit:after', {}, function () {
            edit_after = true;
        });
        return l.appendTo($fix)
            .then(l.proxy('reload_content'))
            .then(function () {
                ok(l.options.editable, "should be editable");
                return l.start_edition();
            })
            // cancelling an event rejects the deferred
            .then($.Deferred().reject(), function () {
                ok(!l.editor.is_editing(), "should not be editing");
                ok(!edit_after, "should not have fired the edit:after event");
                return $.when();
            });
    });
});

openerp.testing.section('list.edition.onwrite', {
    dependencies: ['web.list_editable'],
    rpc: 'mock',
    templates: true,
    setup: function (instance, $s, mock) {
        mock('demo:onchange', function () {
            return {};
        });
    }
}, function (test) {
    test('record-to-read', {asserts: 4}, function (instance, $fix, mock) {
        mock('demo:fields_view_get', function () {
            return {
                type: 'tree',
                fields: {
                    a: {type: 'char', string: "A"}
                },
                arch: '<tree on_write="on_write" colors="red:a == \'foo\'"><field name="a"/></tree>',
            };
        });
        mock('demo:read', function (args, kwargs) {
            if (_.isEmpty(args[0])) {
                return [];
            }
            throw new Error(JSON.stringify(_.toArray(arguments)));
        });
        mock('demo:search_read', function (args, kwargs) {
            if (_.isEqual(args[0], [['id', 'in', [1]]])) {
                return [{id: 1, a: 'some value'}];
            } else if (_.isEqual(args[0], [['id', 'in', [42]]])) {
                return [ {id: 42, a: 'foo'} ];
            }
            throw new Error(JSON.stringify(_.toArray(arguments)));
        });
        mock('demo:default_get', function () { return {}; });
        mock('demo:create', function () { return 1; });
        mock('demo:on_write', function () { return [42]; });

        var ds = new instance.web.DataSetStatic(null, 'demo', null, []);
        var l = new instance.web.ListView({}, ds, false, {editable: 'top'});
        return l.appendTo($fix)
        .then(l.proxy('reload_content'))
        .then(function () {
            return l.start_edition();
        })
        .then(function () {
            $fix.find('.oe_form_field input').val("some value").change();
        })
        .then(function () {
            return l.save_edition();
        })
        .then(function () {
            strictEqual(ds.ids.length, 2,
                'should have id of created + on_write');
            strictEqual(l.records.length, 2,
                'should have record of created + on_write');
            strictEqual(
                $fix.find('tbody tr:eq(1)').css('color'), 'rgb(255, 0, 0)',
                'shoud have color applied');
            notStrictEqual(
                $fix.find('tbody tr:eq(2)').css('color'), 'rgb(255, 0, 0)',
                'should have default color applied');
        });
    });
});
