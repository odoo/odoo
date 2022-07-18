odoo.define('web.domain_tests', function (require) {
"use strict";

var Domain = require('web.Domain');

QUnit.module('core', {}, function () {

    QUnit.module('domain');

    QUnit.test("empty", function (assert) {
        assert.expect(1);
        assert.ok(new Domain([]).compute({}));
    });

    QUnit.test("basic", function (assert) {
        assert.expect(3);

        var fields = {
            a: 3,
            group_method: 'line',
            select1: 'day',
            rrule_type: 'monthly',
        };
        assert.ok(new Domain([['a', '=', 3]]).compute(fields));
        assert.ok(new Domain([['group_method','!=','count']]).compute(fields));
        assert.ok(new Domain([['select1','=','day'], ['rrule_type','=','monthly']]).compute(fields));
    });

    QUnit.test("or", function (assert) {
        assert.expect(3);

        var web = {
            section_id: null,
            user_id: null,
            member_ids: null,
        };
        var currentDomain = [
            '|',
                ['section_id', '=', 42],
                '|',
                    ['user_id', '=', 3],
                    ['member_ids', 'in', [3]]
        ];
        assert.ok(new Domain(currentDomain).compute(_.extend({}, web, {section_id: 42})));
        assert.ok(new Domain(currentDomain).compute(_.extend({}, web, {user_id: 3})));
        assert.ok(new Domain(currentDomain).compute(_.extend({}, web, {member_ids: 3})));
    });

    QUnit.test("not", function (assert) {
        assert.expect(2);

        var fields = {
            a: 5,
            group_method: 'line',
        };
        assert.ok(new Domain(['!', ['a', '=', 3]]).compute(fields));
        assert.ok(new Domain(['!', ['group_method','=','count']]).compute(fields));
    });

    QUnit.test("domains initialized with a number", function (assert) {
        assert.expect(2);

        assert.ok(new Domain(1).compute({}));
        assert.notOk(new Domain(0).compute({}));
    });

    QUnit.test("invalid domains should not succeed", function (assert) {
        assert.expect(3);
        assert.throws(
            () => new Domain(['|', ['hr_presence_state', '=', 'absent']]),
            /invalid domain .* \(missing 1 segment/
        );
        assert.throws(
            () => new Domain(['|', '|', ['hr_presence_state', '=', 'absent'], ['attendance_state', '=', 'checked_in']]),
            /invalid domain .* \(missing 1 segment/
        );
        assert.throws(
            () => new Domain(['&', ['composition_mode', '!=', 'mass_post']]),
            /invalid domain .* \(missing 1 segment/
        );
    });

    QUnit.test("domain <=> condition", function (assert) {
        assert.expect(4);

        var domain = [
            '|',
                '|',
                    '|',
                        '&', ['doc.amount', '>', 33], ['doc.toto', '!=', null],
                        '&', ['doc.bidule.active', '=', true], ['truc', 'in', [2, 3]],
                    ['gogo', '=', 'gogo value'],
                ['gogo', '!=', false]
        ];
        var condition = '((doc.amount > 33 and doc.toto is not None or doc.bidule.active is True and truc in [2,3]) or gogo == "gogo value") or gogo';

        assert.equal(Domain.prototype.domainToCondition(domain), condition);
        assert.deepEqual(Domain.prototype.conditionToDomain(condition), domain);
        assert.deepEqual(Domain.prototype.conditionToDomain(
            'doc and toto is None or not tata'),
            ['|', '&', ['doc', '!=', false], ['toto', '=', null], ['tata', '=', false]]);
        assert.deepEqual(Domain.prototype.conditionToDomain(
            `field in ("foo", "bar") and display_name in ['boo','far']`),
            ['&', ['field', 'in', ['foo', 'bar']], ['display_name', 'in', ['boo', 'far']]]);
    });

    QUnit.test("condition 'a field is set' does not convert to a domain", function (assert) {
        assert.expect(1);
        var expected = [["doc.blabla","!=",false]];
        var condition = "doc.blabla";

        var actual = Domain.prototype.conditionToDomain(condition);

        assert.deepEqual(actual, expected);
    });

    QUnit.test("condition with a function should fail", function (assert) {
        assert.expect(1);
        var condition = "doc.blabla()";

        assert.throws(function() { Domain.prototype.conditionToDomain(condition); });
    });

    QUnit.test("empty condition should not fail", function (assert) {
        assert.expect(2);
        var condition = "";
        var actual = Domain.prototype.conditionToDomain(condition);
        assert.strictEqual(typeof(actual),typeof([]));
        assert.strictEqual(actual.length, 0);
    });
    QUnit.test("undefined condition should not fail", function (assert) {
        assert.expect(2);
        var condition = undefined;
        var actual = Domain.prototype.conditionToDomain(condition);
        assert.strictEqual(typeof(actual),typeof([]));
        assert.strictEqual(actual.length, 0);
    });

    QUnit.test("compute true domain", function (assert) {
        assert.expect(1);
        assert.ok(new Domain(Domain.TRUE_DOMAIN).compute({}));
    });

    QUnit.test("compute false domain", function (assert) {
        assert.expect(1);
        assert.notOk(new Domain(Domain.FALSE_DOMAIN).compute({}));
    });

    QUnit.test("arrayToString", function (assert) {
        assert.expect(14);

        const arrayToString = Domain.prototype.arrayToString;

        // domains containing null, false or true
        assert.strictEqual(arrayToString([['name', '=', null]]), '[["name","=",None]]');
        assert.strictEqual(arrayToString([['name', '=', false]]), '[["name","=",False]]');
        assert.strictEqual(arrayToString([['name', '=', true]]), '[["name","=",True]]');
        assert.strictEqual(arrayToString([['name', '=', 'null']]), '[["name","=","null"]]');
        assert.strictEqual(arrayToString([['name', '=', 'false']]), '[["name","=","false"]]');
        assert.strictEqual(arrayToString([['name', '=', 'true']]), '[["name","=","true"]]');
        assert.strictEqual(arrayToString([['name', 'in', [true, false]]]), '[["name","in",[True,False]]]');
        assert.strictEqual(arrayToString([['name', 'in', [null]]]), '[["name","in",[None]]]');

        assert.strictEqual(arrayToString([['name', 'in', ["foo", "bar"]]]), '[["name","in",["foo","bar"]]]');
        assert.strictEqual(arrayToString([['name', 'in', [1, 2]]]), '[["name","in",[1,2]]]');
        assert.strictEqual(arrayToString(), '[]');

        assert.strictEqual(arrayToString(['&', ['name', '=', 'foo'], ['type', '=', 'bar']]), '["&",["name","=","foo"],["type","=","bar"]]');
        assert.strictEqual(arrayToString(['|', ['name', '=', 'foo'], ['type', '=', 'bar']]), '["|",["name","=","foo"],["type","=","bar"]]');

        // string domains are not processed
        assert.strictEqual(arrayToString('[["name", "ilike", "foo"]]'), '[["name", "ilike", "foo"]]');
    });

    QUnit.test("like, =like, ilike and =ilike", function (assert) {
        assert.expect(16);

        assert.ok(new Domain([['a', 'like', 'value']]).compute({ a: 'value' }));
        assert.ok(new Domain([['a', 'like', 'value']]).compute({ a: 'some value' }));
        assert.notOk(new Domain([['a', 'like', 'value']]).compute({ a: 'Some Value' }));
        assert.notOk(new Domain([['a', 'like', 'value']]).compute({ a: false }));

        assert.ok(new Domain([['a', '=like', '%value']]).compute({ a: 'value' }));
        assert.ok(new Domain([['a', '=like', '%value']]).compute({ a: 'some value' }));
        assert.notOk(new Domain([['a', '=like', '%value']]).compute({ a: 'Some Value' }));
        assert.notOk(new Domain([['a', '=like', '%value']]).compute({ a: false }));

        assert.ok(new Domain([['a', 'ilike', 'value']]).compute({ a: 'value' }));
        assert.ok(new Domain([['a', 'ilike', 'value']]).compute({ a: 'some value' }));
        assert.ok(new Domain([['a', 'ilike', 'value']]).compute({ a: 'Some Value' }));
        assert.notOk(new Domain([['a', 'ilike', 'value']]).compute({ a: false }));

        assert.ok(new Domain([['a', '=ilike', '%value']]).compute({ a: 'value' }));
        assert.ok(new Domain([['a', '=ilike', '%value']]).compute({ a: 'some value' }));
        assert.ok(new Domain([['a', '=ilike', '%value']]).compute({ a: 'Some Value' }));
        assert.notOk(new Domain([['a', '=ilike', '%value']]).compute({ a: false }));
    });
});
});
