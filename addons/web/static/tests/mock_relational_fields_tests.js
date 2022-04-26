/** @odoo-module **/

import { MockServer } from "@web/../tests/helpers/mock_server";

QUnit.module('web', {}, function () {
QUnit.module('mock_relational_fields_tests.js', {
    beforeEach() {
        this.models = {
            foo: {
                fields: {
                    one2many_field: { type: 'one2many', relation: 'bar', inverse_fname_by_model_name: { bar: 'many2one_field' } },
                    many2one_field: { type: 'many2one', relation: 'bar', inverse_fname_by_model_name: { bar: 'one2many_field' } },
                    many2many_field: { type: 'many2many', relation: 'bar', inverse_fname_by_model_name: { bar: 'many2many_field' } },
                    many2one_reference: { type: 'many2one_reference', model_name_ref_fname: 'res_model', inverse_fname_by_model_name: { bar: 'one2many_field' } },
                    res_model: { type: 'char' },

                },
                records: [],
            },
            bar: {
                fields: {
                    many2one_field: { type: 'many2one', relation: 'foo' },
                    one2many_field: { type: 'one2many', relation: 'foo', inverse_fname_by_model_name: { foo: 'many2one_field' } },
                    many2many_field: { type: 'many2many', relation: 'foo', inverse_fname_by_model_name: { foo: 'many2many_field' } },
                },
                records: [],
            },
        };
    }
});

QUnit.test('many2one_ref should auto fill inverse field', async function (assert) {
    this.models['bar'].records.push({ id: 1 });
    this.models['foo'].records.push({
        id: 2,
        res_model: 'bar',
        many2one_reference: 1,
    });
    const mockServer = new MockServer({ models: this.models });
    assert.deepEqual([2], mockServer.models['bar'].records[0].one2many_field);

    mockServer.mockUnlink('foo', [2]);
    assert.deepEqual([], mockServer.models['bar'].records[0].one2many_field);
});

QUnit.test('many2one should auto fill inverse field', async function (assert) {
    this.models['bar'].records.push({ id: 1 });
    this.models['foo'].records.push({
        id: 2,
        many2one_field: 1,
    });
    const mockServer = new MockServer({ models: this.models });
    assert.deepEqual([2], mockServer.models['bar'].records[0].one2many_field);

    mockServer.mockUnlink('foo', [2]);
    assert.deepEqual([], mockServer.models['bar'].records[0].one2many_field);
});

QUnit.test('one2many should auto fill inverse field', async function (assert) {
    this.models['bar'].records.push({ id: 1 });
    this.models['bar'].records.push({ id: 2 });
    this.models['foo'].records.push({
        id: 3,
        one2many_field: [1, 2],
    });
    const mockServer = new MockServer({ models: this.models });
    assert.strictEqual(3, mockServer.models['bar'].records[0].many2one_field);
    assert.strictEqual(3, mockServer.models['bar'].records[1].many2one_field);

    mockServer.mockUnlink('foo', [3]);
    assert.strictEqual(false, mockServer.models['bar'].records[0].many2one_field);
    assert.strictEqual(false, mockServer.models['bar'].records[1].many2one_field);
});

QUnit.test('many2many should auto fill inverse field', async function (assert) {
    this.models['bar'].records.push({ id: 1 });
    this.models['foo'].records.push({
        id: 2,
        many2many_field: [1],
    });
    const mockServer = new MockServer({ models: this.models });
    assert.deepEqual([2], mockServer.models['bar'].records[0].many2many_field);

    mockServer.mockUnlink('foo', [2]);
    assert.deepEqual([], mockServer.models['bar'].records[0].many2many_field);
});

QUnit.test('one2many update should update inverse field', async function (assert) {
    this.models['bar'].records.push({ id: 1 });
    this.models['bar'].records.push({ id: 2 });
    this.models['foo'].records.push({
        id: 3,
        one2many_field: [1, 2],
    });
    const mockServer = new MockServer({ models: this.models });
    mockServer.mockWrite('foo', [[3], { one2many_field: [1] }]);
    assert.strictEqual(3, mockServer.models['bar'].records[0].many2one_field);
    assert.strictEqual(false, mockServer.models['bar'].records[1].many2one_field);
});

QUnit.test('many2many update should update inverse field', async function (assert) {
    this.models['bar'].records.push({ id: 1 });
    this.models['foo'].records.push({
        id: 2,
        many2many_field: [1],
    });
    const mockServer = new MockServer({ models: this.models });
    mockServer.mockWrite('foo', [[2], { many2many_field: [] }]);
    assert.deepEqual([], mockServer.models['bar'].records[0].many2many_field);
});

QUnit.test('many2one update should update inverse field', async function (assert) {
    this.models['bar'].records.push({ id: 1 });
    this.models['foo'].records.push({
        id: 2,
        many2one_field: 1,
    });
    const mockServer = new MockServer({ models: this.models });
    mockServer.mockWrite('foo', [[2], { many2one_field: false }]);
    assert.deepEqual([], mockServer.models['bar'].records[0].one2many_field);
});

QUnit.test('many2one_ref update should update inverse field', async function (assert) {
    this.models['bar'].records.push({ id: 1 });
    this.models['foo'].records.push({
        id: 2,
        res_model: 'bar',
        many2one_reference: 1,
    });
    const mockServer = new MockServer({ models: this.models });
    mockServer.mockWrite('foo', [[2], { many2one_reference: false }]);
    assert.deepEqual([], mockServer.models['bar'].records[0].one2many_field);
});

});
