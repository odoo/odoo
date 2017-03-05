odoo.define('web.domain_tests', function (require) {
"use strict";

var Domain = require('web.Domain');

QUnit.module('core', {}, function () {

    QUnit.module('domain');

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
});
});
