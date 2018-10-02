odoo.define('web.currency_tests', function (require) {
'use strict';

var AbstractView = require('web.AbstractView');
var CurrencyService = require('web.CurrencyService');
var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;
var rpcResponse = {
    currencies: {
        1: { symbol: '$', position: 'before' },
        2: { symbol: '€', position: 'after' },
    },
};

QUnit.module('Services', {
    beforeEach: function () {
        this.viewParams = {
            View: AbstractView,
            arch: '<fake/>',
            data: {
                fake_model: {
                    fields: {},
                    record: [],
                },
                currency: {
                    fields: {
                        symbol: {string: "Currency Sumbol", type: "char"},
                        position: {string: "Currency Position", type: "char"},
                        active: {string: "Active", type: "boolean"},
                    },
                    records: [{
                        id: 2,
                        display_name: "€",
                        symbol: "€",
                        position: "after",
                        active: false,
                    }]
                },
            },
            model: 'fake_model',
            services: {
                currency: CurrencyService,
            },
            session: {
                currencies: {
                    1: { symbol: '$', position: 'before' },
                },
            },
            mockRPC: function (route, args) {
                if (route === '/web/session/get_session_info') {
                    return $.when($.extend(true, {}, rpcResponse));
                }
                return this._super.apply(this, arguments);
            },
        };
    }
}, function () {
    QUnit.module('Currency');

    QUnit.test('correctly reload currency info', function (assert) {
        assert.expect(3);

        var view = createView(this.viewParams);
        var session = view.getSession();

        assert.notDeepEqual( session.currencies, rpcResponse.currencies,
            'have one currency by default');
        view.call('currency', 'reload', 1);
        assert.notDeepEqual( session.currencies, rpcResponse.currencies,
            'don\'t get more currencies if call one we have already');
        view.call('currency', 'reload', 2);
        assert.deepEqual( session.currencies, rpcResponse.currencies,
            'have two currencies after the call');

        view.destroy();
    });

    QUnit.test('switch a currency call the service', function (assert) {
        assert.expect(2);

        var data = this.viewParams.data;
        // basic model call currency service only for 'res.currency' model
        data['res.currency'] = data.currency;

        var params = this.viewParams;
        params.model = 'res.currency';
        params.arch = '<form>'+
                '<field name="display_name"/>'+
                '<field name="active" widget="boolean_toggle"/>'+
            '</form>';
        params.View = FormView;
        params.res_id = 2;

        var form = createView(params);
        var session = form.getSession();

        assert.notDeepEqual( session.currencies, rpcResponse.currencies,
            'have one currency by default');
        form.$('.custom-checkbox.o_boolean_toggle').click();
        assert.deepEqual( session.currencies, rpcResponse.currencies,
            'have a second currency after switch the toggle');

        form.destroy();
    });
});});
