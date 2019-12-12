odoo.define('web.loading_tests', function (require) {
"use strict";

const core = require('web.core');
const Loading = require('web.Loading');

QUnit.module('widgets', {}, function () {

QUnit.module('Loading', {}, function () {
    QUnit.test("render the loading widget", async function (assert) {
        assert.expect(6);

        const target = document.getElementById('qunit-fixture');
        const loading = new Loading();
        await loading.appendTo(target);

        assert.containsOnce(target, '.o_loading');
        assert.strictEqual(loading.count, 0);

        core.bus.trigger('rpc_request');

        assert.strictEqual(loading.count, 1);
        assert.strictEqual(loading.el.style.display, '');

        core.bus.trigger('rpc_response');
        // wait for the fade out...
        await new Promise(resolve => {
            setTimeout(resolve, 500);
        });

        assert.strictEqual(loading.count, 0);
        assert.strictEqual(loading.el.style.display, 'none');

        loading.destroy();
    });

    QUnit.test("block ui", async function (assert) {
        assert.expect(4);

        const target = document.getElementById('qunit-fixture');
        const loading = new Loading();
        await loading.appendTo(target);

        core.bus.trigger('rpc_request');
        // wait for more than 3 seconds to block the ui
        await new Promise(resolve => {
            setTimeout(resolve, 3500);
        });

        assert.ok(document.body.classList.contains('o_ui_blocked'));
        assert.containsOnce(document.body, '.blockUI.blockOverlay');

        core.bus.trigger('rpc_response');
        assert.ok(!document.body.classList.contains('o_ui_blocked'));

        // wait a bit for the blockUI overlay to fade out...
        await new Promise(resolve => {
            setTimeout(resolve, 500);
        });
        assert.containsNone(document.body, '.blockUI.blockOverlay');

        loading.destroy();
    });
});
});
});
