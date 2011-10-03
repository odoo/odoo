var py = require('../lib/py.js'),
    assert = require('assert');

// Literals
assert.strictEqual(py.eval('1'), 1);
assert.strictEqual(py.eval('None'), null);
assert.strictEqual(py.eval('False'), false);
assert.strictEqual(py.eval('True'), true);
assert.strictEqual(py.eval('"somestring"'), 'somestring');
assert.strictEqual(py.eval("'somestring'"), 'somestring');
assert.deepEqual(py.eval("()").toJSON(), []);
assert.deepEqual(py.eval("[]").toJSON(), []);
assert.deepEqual(py.eval("{}").toJSON(), {});
assert.deepEqual(py.eval("(None, True, False, 0, 1, 'foo')").toJSON(),
                 [null, true, false, 0, 1, 'foo']);
assert.deepEqual(py.eval("[None, True, False, 0, 1, 'foo']").toJSON(),
                 [null, true, false, 0, 1, 'foo']);
assert.deepEqual(py.eval("{'foo': 1, foo: 2}", {foo: 'bar'}).toJSON(),
                 {foo: 1, bar: 2});

// Equality tests
assert.ok(py.eval(
    "foo == 'foo'", {foo: 'foo'}));
// Inequality
assert.ok(py.eval(
    "foo != bar", {foo: 'foo', bar: 'bar'}));

// Comparisons
assert.ok(py.eval('3 < 5'));
assert.ok(py.eval('5 >= 3'));
assert.ok(py.eval('3 >= 3'));
assert.ok(!py.eval('5 < 3'));
assert.ok(py.eval('1 < 3 < 5'));
assert.ok(py.eval('5 > 3 > 1'));
assert.ok(py.eval('1 < 3 > 2 == 2 > -2 not in (0, 1, 2)'));
// string rich comparisons
assert.ok(py.eval(
    'date >= current', {date: '2010-06-08', current: '2010-06-05'}));

// Boolean operators
assert.ok(py.eval(
    "foo == 'foo' or foo == 'bar'", {foo: 'bar'}));
assert.ok(py.eval(
    "foo == 'foo' and bar == 'bar'", {foo: 'foo', bar: 'bar'}));
// - lazyness, second clauses NameError if not short-circuited
assert.ok(py.eval(
    "foo == 'foo' or bar == 'bar'", {foo: 'foo'}));
assert.ok(!py.eval(
    "foo == 'foo' and bar == 'bar'", {foo: 'bar'}));

// contains (in)
assert.ok(py.eval(
    "foo in ('foo', 'bar')", {foo: 'bar'}));
assert.ok(py.eval('1 in (1, 2, 3, 4)'));
assert.ok(!py.eval('1 in (2, 3, 4)'));
assert.ok(py.eval('type in ("url",)', {type: 'url'}));
assert.ok(!py.eval('type in ("url",)', {type: 'ur'}));
assert.ok(py.eval('1 not in (2, 3, 4)'));
assert.ok(py.eval('type not in ("url",)', {type: 'ur'}));

assert.ok(py.eval(
    "foo in ['foo', 'bar']", {foo: 'bar'}));
// string contains
assert.ok(py.eval('type in "view"', {type: 'view'}));
assert.ok(!py.eval('type in "view"', {type: 'bob'}));
assert.ok(py.eval('type in "url"', {type: 'ur'}));

// Literals
assert.strictEqual(py.eval('False'), false);
assert.strictEqual(py.eval('True'), true);
assert.strictEqual(py.eval('None'), null);
assert.ok(py.eval('foo == False', {foo: false}));
assert.ok(!py.eval('foo == False', {foo: true}));

// conversions
assert.strictEqual(
    py.eval('bool(date_deadline)', {bool: py.bool, date_deadline: '2008'}),
    true);

// getattr
assert.ok(py.eval('foo.bar', {foo: {bar: true}}));
assert.ok(!py.eval('foo.bar', {foo: {bar: false}}));

// complex expressions
assert.ok(py.eval(
    "state=='pending' and not(date_deadline and (date_deadline < current_date))",
    {state: 'pending', date_deadline: false}));
assert.ok(py.eval(
    "state=='pending' and not(date_deadline and (date_deadline < current_date))",
    {state: 'pending', date_deadline: '2010-05-08', current_date: '2010-05-08'}));;
