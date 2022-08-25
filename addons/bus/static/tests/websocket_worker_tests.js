/** @odoo-module */

import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";
import { patchWebsocketWorkerWithCleanup } from '@bus/../tests/helpers/mock_websocket';

import { nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module('Websocket Worker');
QUnit.test('connect event is broadcasted', async function (assert) {
    assert.expect(2);

    patchWebsocketWorkerWithCleanup({
        broadcast(type) {
            assert.step(`broadcast ${type}`);
        },
    });
    // Wait for the websocket to connect.
    await nextTick();
    assert.verifySteps(['broadcast connect']);
});

QUnit.test('disconnect event is broadcasted', async function (assert) {
    assert.expect(3);

    const worker = patchWebsocketWorkerWithCleanup({
        broadcast(type) {
            assert.step(`broadcast ${type}`);
        },
    });
    // Wait for the websocket to connect.
    await nextTick();
    worker.websocket.close(WEBSOCKET_CLOSE_CODES.CLEAN);
    // Wait for the websocket to disconnect.
    await nextTick();

    assert.verifySteps([
        'broadcast connect',
        'broadcast disconnect',
    ]);
});

QUnit.test('reconnecting/reconnect event is broadcasted', async function (assert) {
    assert.expect(5);

    // Patch setTimeout in order for the worker to reconnect immediatly.
    patchWithCleanup(window, {
        setTimeout: fn => fn(),
    });
    const worker = patchWebsocketWorkerWithCleanup({
        broadcast(type) {
            assert.step(`broadcast ${type}`);
        },
    });
    // Wait for the websocket to connect.
    await nextTick();
    worker.websocket.close(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    // Wait for the disconnect/reconnecting/reconnect events.
    await nextTick();

    assert.verifySteps([
        'broadcast connect',
        'broadcast disconnect',
        'broadcast reconnecting',
        'broadcast reconnect',
    ]);
});

QUnit.test('notification event is broadcasted', async function (assert) {
    assert.expect(3);

    const notifications = [{
        id: 70,
        message: {
            type: "bundle_changed",
            payload: {
                server_version: '15.5alpha1+e',
            },
        },
    }];
    const worker = patchWebsocketWorkerWithCleanup({
        broadcast(type, message) {
            if (type === 'notification') {
                assert.step(`broadcast ${type}`);
                assert.deepEqual(message, notifications.map(notif => notif.message));
            }
        },
    });
    // Wait for the websocket to connect.
    await nextTick();

    worker.websocket.dispatchEvent(new MessageEvent('message', {
        data: JSON.stringify(notifications),
    }));

    assert.verifySteps([
        'broadcast notification',
    ]);
});
