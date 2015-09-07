odoo.define_section('editor', ['web.ListEditor'], function (test, mock) {

    function setup() {
        mock.add('test.model:create', function () {
            return 42;
        });
        mock.add('test.model:onchange', function () {
            return {};
        });
    }

    function field(name, attrs) {
        attrs = attrs || {};
        attrs.name = name;
        return _.defaults(attrs, {
            type: 'char'
        });
    }

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

    test('base-state', ['web.FormView'], function (assert, ListEditor, FormView) {
        var e = new ListEditor({
            dataset: {ids: []},
            edition_view: function () {
                return makeFormView();
            }
        });
        var $fix = $( "#qunit-fixture");
        return e.appendTo($fix)
            .done(function () {
                ok(!e.is_editing(), "should not be editing");
                ok(e.form instanceof FormView, "should use default form type");
            });
    });

    test('toggle-edition-save', ['web.data'], function (assert, ListEditor, data) {
        setup();
        assert.expect(4);

        mock.add('test.model:search_read', function () {
            return [{id: 42, a: false, b: false, c: false}];
        });

        var e = new ListEditor({
            dataset: new data.DataSetSearch(null, 'test.model'),
            prepends_on_create: function () { return false; },
            edition_view: function () {
                return makeFormView([ field('a'), field('b'), field('c') ]);
            }
        });
        var counter = 0;
        var $fix = $( "#qunit-fixture");
        return e.appendTo($fix)
            .then(function () {
                return e.edit({}, function () {
                    ++counter;
                });
            })
            .then(function (form) {
                assert.ok(e.is_editing(), "should be editing");
                assert.equal(counter, 3, "should have configured all fields");
                return e.save().then(function() {
                    return e.cancel();
                });
            })
            .done(function (record) {
                assert.ok(!e.is_editing(), "should have stopped editing");
                assert.equal(record.id, 42, "should have newly created id");
            });
    });

    test('toggle-edition-cancel', ['web.data'], function (assert, ListEditor, data) {
        assert.expect(2);

        var e = new ListEditor({
            dataset: new data.DataSetSearch(null, 'test.model'),
            prepends_on_create: function () { return false; },
            edition_view: function () {
                return makeFormView([ field('a'), field('b'), field('c') ]);
            }
        });
        var counter = 0;
        var $fix = $( "#qunit-fixture");
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

    test('toggle-save-required', ['web.core', 'web.data'], function (assert, ListEditor, core, data) {
        var done = assert.async();
        assert.expect(2);

        var warnings = 0;

        var e = new ListEditor({
            dataset: new data.DataSetSearch(null, 'test.model'),
            prepends_on_create: function () { return false; },
            edition_view: function () {
                return makeFormView([
                    field('a', {required: true}), field('b'), field('c') ]);
            },
            _trigger_up: function (event) {
                if (event.name === 'warning') {
                    warnings++;
                }
            },
        });
        var counter = 0;
        var $fix = $( "#qunit-fixture");

        e.appendTo($fix)
            .then(function () {
                return e.edit({}, function () {
                    ++counter;
                });
            })
            .then(function (form) {
                return e.save().then(function() {
                    return e.cancel();
                });
            })
            .done(function () { assert.ok(false, "cancel should not succeed"); })
            .fail(function () {
                assert.equal(warnings, 1, "should have been warned");
                assert.ok(e.is_editing(), "should have kept editing");
                done();
            });
    });
});

odoo.define_section('list.edition', ['web.data', 'web.ListView'], function (test, mock) {

    function setup () {
        var records = {};
        mock.add('demo:create', function (args) {
            records[42] = _.extend({}, args[0]);
            return 42;
        });
        mock.add('demo:read', function (args) {
            var id = args[0][0];
            if (id in records) {
                return [records[id]];
            }
            return [];
        });
        mock.add('demo:search_read', function (args) {
            var id = args[0][0][2];
            if (id in records) {
                return [records[id]];
            }
            return [];
        });
        mock.add('demo:fields_view_get', function () {
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
        mock.add('demo:onchange', function () {
            return {};
        });
    }

    test('newrecord', function (assert, data, ListView) {
        setup();
        assert.expect(6);
        var got_defaults = false;

        mock.add('demo:default_get', function (args) {
            var fields = args[0];
            assert.deepEqual(
                fields, ['a', 'b', 'c'],
                "should ask defaults for all fields");
            got_defaults = true;
            return { a: "qux", b: "quux" };
        });

        var ds = new data.DataSetStatic(null, 'demo', null, [1]);
        var l = new ListView({}, ds, false, {editable: 'top'});

        var $fix = $( "#qunit-fixture");
        return l.appendTo($fix)
            .then(l.proxy('reload_content'))
            .then(function () {
                return l.start_edition();
            })
            .then(function () {
                assert.ok(got_defaults, "should have fetched default values for form");

                return l.save_edition();
            })
            .then(function (result) {
                assert.ok(result.created, "should yield newly created record");
                assert.equal(result.record.get('a'), "qux",
                      "should have used default values");
                assert.equal(result.record.get('b'), "quux",
                      "should have used default values");
                assert.ok(!result.record.get('c'),
                    "should have no value if there was no default");
            });
    });
});

odoo.define_section('list.edition.events', ['web.data', 'web.ListView'], function (test, mock) {

    function setup () {
        mock.add('demo:read', function () {
            return [{ id: 1, a: 'foo', b: 'bar', c: 'baz' }];
        });
        mock.add('demo:fields_view_get', function () {
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

    test('edition events',function (assert, data, ListView) {
        setup();
        assert.expect(4);
        var ds = new data.DataSetStatic(null, 'demo', null, [1]);
        var o = {
            counter: 0,
            onEvent: function (e) { this.counter++; }
        };
        var l = new ListView({}, ds, false, {editable: 'top'});
        l.on('edit:before edit:after', o, o.onEvent);

        var $fix = $( "#qunit-fixture");
        return l.appendTo($fix)
            .then(l.proxy('reload_content'))
            .then(function () {
                assert.ok(l.options.editable, "should be editable");
                assert.equal(o.counter, 0, "should have seen no event yet");
                return l.start_edition(l.records.get(1));
            })
            .then(function () {
                assert.ok(l.editor.is_editing(), "should be editing");
                assert.equal(o.counter, 2, "should have seen two edition events");
            });
    });

    test('edition events: cancelling', function (assert, data, ListView) {
        setup();
        var edit_after = false;
        var ds = new data.DataSetStatic(null, 'demo', null, [1]);
        var l = new ListView({}, ds, false, {editable: 'top'});
        l.on('edit:before', {}, function (e) {
            e.cancel = true;
        });
        l.on('edit:after', {}, function () {
            edit_after = true;
        });

        var $fix = $( "#qunit-fixture");
        return l.appendTo($fix)
            .then(l.proxy('reload_content'))
            .then(function () {
                assert.ok(l.options.editable, "should be editable");
                return l.start_edition();
            })
            // cancelling an event rejects the deferred
            .then($.Deferred().reject(), function () {
                assert.ok(!l.editor.is_editing(), "should not be editing");
                assert.ok(!edit_after, "should not have fired the edit:after event");
                return $.when();
            });
    });
});

odoo.define_section('list.edition.onwrite', ['web.data', 'web.ListView'], function (test, mock) {

    test('record-to-read', function (assert, data, ListView) {
        assert.expect(4);

        mock.add('demo:onchange', function () {
            return {};
        });

        mock.add('demo:fields_view_get', function () {
            return {
                type: 'tree',
                fields: {
                    a: {type: 'char', string: "A"}
                },
                arch: '<tree on_write="on_write" colors="red:a == \'foo\'"><field name="a"/></tree>',
            };
        });
        mock.add('demo:read', function (args, kwargs) {
            if (_.isEmpty(args[0])) {
                return [];
            }
            throw new Error(JSON.stringify(_.toArray(arguments)));
        });
        mock.add('demo:search_read', function (args, kwargs) {
            if (_.isEqual(args[0], [['id', 'in', [1]]])) {
                return [{id: 1, a: 'some value'}];
            } else if (_.isEqual(args[0], [['id', 'in', [42]]])) {
                return [ {id: 42, a: 'foo'} ];
            }
            throw new Error(JSON.stringify(_.toArray(arguments)));
        });
        mock.add('demo:default_get', function () { return {}; });
        mock.add('demo:create', function () { return 1; });
        mock.add('demo:on_write', function () { return [42]; });

        var ds = new data.DataSetStatic(null, 'demo', null, []);
        var l = new ListView({}, ds, false, {editable: 'top'});

        var $fix = $( "#qunit-fixture");
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
            assert.strictEqual(ds.ids.length, 2,
                'should have id of created + on_write');
            assert.strictEqual(l.records.length, 2,
                'should have record of created + on_write');
            assert.strictEqual(
                $fix.find('tbody tr:eq(1)').css('color'), 'rgb(255, 0, 0)',
                'shoud have color applied');
            assert.notStrictEqual(
                $fix.find('tbody tr:eq(2)').css('color'), 'rgb(255, 0, 0)',
                'should have default color applied');
        });
    });
});

