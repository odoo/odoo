/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import {
    parseTextualSelection,
    setTestSelection,
    renderTextualSelection,
    patchEditorIframe,
} from '@web_editor/js/editor/odoo-editor/test/utils';
import { Wysiwyg, stripHistoryIds } from '@web_editor/js/wysiwyg/wysiwyg';
import { Mutex } from '@web/core/utils/concurrency';
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import { mount, getFixture } from "@web/../tests/helpers/utils";
import { registry } from "@web/core/registry";

export function makeSpy(obj, functionName) {
    const spy = {
        callCount: 0,
    };
    patch(obj, {
        [functionName]() {
            spy.callCount++;
            return super[functionName].apply(this, arguments);
        }
    });
    return spy;
}
export function makeSpies(obj, methodNames) {
    const methods = {};
    for (const methodName of methodNames) {
        methods[methodName] = makeSpy(obj, methodName);
    }
    return methods;
}

class PeerTest {
    constructor(infos) {
        this.peerId = infos.peerId;
        this.wysiwyg = infos.wysiwyg;
        this.iframe = infos.iframe;
        this.document = this.iframe.contentWindow.document;
        this.wrapper = infos.wrapper;
        this.pool = infos.pool;
        this.peers = infos.pool.peers;
        this._connections = new Set();
        this.onlineMutex = new Mutex();
        this.isOnline = true;
    }
    async startEditor() {
        this._started = this.wysiwyg.startEdition();
        this.started = true;
        await this._started;
        if (this.initialParsedSelection) {
            await setTestSelection(this.initialParsedSelection, this.document);
            this.wysiwyg.odooEditor._recordHistorySelection();
        } else {
            document.getSelection().removeAllRanges();
        }
        clearInterval(this.wysiwyg._collaborationInterval);
        return this._started;
    }
    async destroyEditor() {
        for (const peer of this._connections) {
            peer._connections.delete(this);
        }
        this.wysiwyg.destroy();
    }
    async focus() {
        await this.started;
        return this.wysiwyg._joinPeerToPeer();
    }
    async openDataChannel(peer) {
        this._connections.add(peer);
        peer._connections.add(this);
        const ptpFrom = this.wysiwyg.ptp;
        const ptpTo = peer.wysiwyg.ptp;
        ptpFrom.clientsInfos[peer.peerId] = {};
        ptpTo.clientsInfos[this.peerId] = {};

        // Simulate the rtc_data_channel_open on both peers.
        await this.wysiwyg.ptp.notifySelf('rtc_data_channel_open', {
            connectionClientId: peer.peerId,
        });
        await peer.wysiwyg.ptp.notifySelf('rtc_data_channel_open', {
            connectionClientId: this.peerId,
        });
    }
    async removeDataChannel(peer) {
        this._connections.delete(peer);
        peer._connections.delete(this);
        const ptpFrom = this.wysiwyg.ptp;
        const ptpTo = peer.wysiwyg.ptp;
        delete ptpFrom.clientsInfos[peer.peerId];
        delete ptpTo.clientsInfos[this.peerId];
        this.onlineMutex = new Mutex();
        this._onlineResolver = undefined;
    }
    async getValue() {
        this.wysiwyg.odooEditor.observerUnactive('PeerTest.getValue');
        renderTextualSelection(this.wysiwyg.odooEditor);

        const html = this.wysiwyg.$editable[0].innerHTML;

        const selection = parseTextualSelection(this.wysiwyg.$editable[0]);
        if (selection) {
            await setTestSelection(selection, this.document);
        }
        this.wysiwyg.odooEditor.observerActive('PeerTest.getValue');

        return stripHistoryIds(html);
    }
    writeToServer() {
        this.pool.lastRecordSaved = this.wysiwyg.getValue();
        const lastId = this.wysiwyg._getLastHistoryStepId(this.pool.lastRecordSaved);
        for (const peer of Object.values(this.peers)) {
            if (peer === this || !peer._started) continue;
            peer.onlineMutex.exec(() => {
                return peer.wysiwyg._onServerLastIdUpdate(String(lastId));
            });
        }
    }
    async setOnline() {
        this.isOnline = true;
        this._onlineResolver && this._onlineResolver();
        return this.onlineMutex.getUnlockedDef();
    }
    setOffline() {
        this.isOnline = false;
        if (this._onlineResolver) return;
        this.onlineMutex.exec(async () => {
            await new Promise((resolve) => {
                this._onlineResolver = () => {
                    this._onlineResolver = null;
                    resolve();
                }
            });
        });
    }
}

const initialValue = '<p data-last-history-steps="1">a[]</p>';

class PeerPool {
    constructor(peers) {
        this.peers = {};
    }
}

export async function createPeers(peers) {
    const pool = new PeerPool();

    let lastGeneratedId = 0;

    for (const peerId of peers) {
        const iframe = document.createElement('iframe');
        if (navigator.userAgent.toLowerCase().indexOf('firefox') > -1) {
            // Firefox reset the page without this hack.
            // With this hack, chrome does not render content.
            iframe.setAttribute('src', ' javascript:void(0);');
        }
        getFixture().append(iframe);
        patchEditorIframe(iframe);
        iframe.contentDocument.body.innerHTML = `<div class="peer_wysiwyg_wrapper client_${peerId}"></div>`;
        const peerWysiwygWrapper = iframe.contentDocument.querySelector('.peer_wysiwyg_wrapper');
        iframe.contentWindow.$ = $;

        registry.category("services").add("notification", makeFakeNotificationService(), {
            force: true,
        });
        registry.category("services").add("popover", { start: () => ({  }) }, {
            force: true,
        });
        const env = await makeTestEnv({
            mockRPC(route) {
                if (route === "/web/dataset/call_kw/res.users/read") {
                    return [{ id: 0, name: "admin" }];
                }
            }
        });

        const wysiwyg = await mount(Wysiwyg, peerWysiwygWrapper, {
            env,
            props: {
                startWysiwyg: () => {},
                options: {
                    value: initialValue,
                    collaborative: true,
                    collaborationChannel: {
                        collaborationFieldName: "fake_field",
                        collaborationModelName: "fake.model",
                        collaborationResId: 1
                    },
                    document: iframe.contentWindow.document,
                }
            }
        });
        patch(wysiwyg, {
            _generateClientId() {
                return peerId;
            },
            // Hacky hook as we know this method is called after setting the value in the wysiwyg start and before sending the value to odooEditor.
            _getLastHistoryStepId() {
                pool.peers[peerId].initialParsedSelection = parseTextualSelection(wysiwyg.$editable[0]);
                return super._getLastHistoryStepId(...arguments);
            },
            _serviceRpc(route, params) {
                if (route === '/web_editor/get_ice_servers') {
                    return [];
                } else if (route === '/web_editor/bus_broadcast') {
                    const currentPeer = pool.peers[peerId];
                    for (const peer of currentPeer._connections) {
                        peer.wysiwyg.ptp.handleNotification(structuredClone(params.bus_data));
                    }
                }
            },
            _getNewPtp() {
                const ptp = super._getNewPtp(...arguments);
                ptp.options.onRequest.get_client_avatar = () => '';

                patch(ptp, {
                    removeClient(peerId) {
                        this.notifySelf('ptp_remove', peerId);
                        delete this.clientsInfos[peerId];
                    },
                    notifyAllClients(...args)  {
                        // This is not needed because the opening of the
                        // dataChannel is done through `openDataChannel` and we
                        // do not want to simulate the events that thrigger the
                        // openning of the dataChannel.
                        if (args[0] === 'ptp_join') {
                            return;
                        }
                        super.notifyAllClients(...args);
                    },
                     _getPtpClients() {
                        return pool.peers[peerId]._connections.map((peer) => {
                            return { id: peer.peerId }
                        });
                     },
                    async _channelNotify(peerId, transportPayload) {
                        if (!pool.peers[peerId].isOnline) return;
                        pool.peers[peerId].wysiwyg.ptp.handleNotification(structuredClone(transportPayload));
                    },

                    _createClient() {
                        throw new Error('Should not be called.');
                    },
                    _addIceCandidate() {
                        throw new Error('Should not be called.');
                    },
                    _recoverConnection() {
                        throw new Error('Should not be called.');
                    },
                    _killPotentialZombie() {
                        throw new Error('Should not be called.');
                    },
                });
                return ptp;
            },
            _getCurrentRecord() {
                return {
                    id: 1,
                    fake_field: pool.lastRecordSaved,
                }
            },
            _getCollaborationClientAvatarUrl() {
                return '';
            },
            async startEdition() {
                await super.startEdition(...arguments);
                patch(this.odooEditor, {
                    _generateId() {
                        // Ensure the id are deterministically gererated for
                        // when we need to sort by them. (eg. in the
                        // callaboration sorting of steps)
                        lastGeneratedId++;
                        return lastGeneratedId.toString();
                    },
                });
            },
            _hasICEServers() {
                return true;
            },
            _showConflictDialog() {},
        });
        pool.peers[peerId] = new PeerTest({
            peerId,
            wysiwyg,
            iframe,
            wrapper: peerWysiwygWrapper,
            pool,
        });
    }
    return pool;
}
export function removePeers(peers) {
    for (const peer of Object.values(peers)) {
        peer.wysiwyg.destroy();
        peer.wrapper.remove();
    }
}

const unpatchs = [];
QUnit.module('web_editor', {
    before() {
        unpatchs.push(
            patch(Wysiwyg, {
                activeCollaborationChannelNames: {
                    has: () => false,
                    add: () => {},
                    delete: () => {},
                },
            })
        );
        unpatchs.push(
            patch(Wysiwyg.prototype, {
                setup() {
                    const result = super.setup(...arguments);
                    this.busService = {
                        addEventListener: () => {},
                        removeEventListener: () => {},
                        addChannel: () => {},
                        deleteChannel: () => {},
                    };
                    return result;
                },
            })
        );
    },
    after() {
        for (const unpatch of unpatchs) {
            unpatch();
        }
    }
}, () => {
    QUnit.module('Collaboration', {}, () => {
        /**
         * Detect stale when <already focused | not already focused>
         */
        QUnit.module('Focus', {}, () => {
            QUnit.test('Focused client should not receive step if no data channel is open', async (assert) => {
                assert.expect(3);
                const pool = await createPeers(['p1', 'p2', 'p3']);
                const peers = pool.peers;

                await peers.p1.startEditor();
                await peers.p2.startEditor();
                await peers.p3.startEditor();

                await peers.p1.focus();
                await peers.p2.focus();

                await peers.p1.wysiwyg.odooEditor.execCommand('insert', 'b');

                assert.equal(await peers.p1.getValue(), `<p>ab[]</p>`, 'p1 should have the document changed');
                assert.equal(await peers.p2.getValue(), `<p>a[]</p>`, 'p2 should not have the document changed');
                assert.equal(await peers.p3.getValue(), `<p>a[]</p>`, 'p3 should not have the document changed');

                removePeers(peers);
            });
            QUnit.test('Focused client should receive step while unfocused should not (if the datachannel is open before the step)', async (assert) => {
                assert.expect(3);
                const pool = await createPeers(['p1', 'p2', 'p3']);
                const peers = pool.peers;

                await peers.p1.startEditor();
                await peers.p2.startEditor();
                await peers.p3.startEditor();

                await peers.p1.focus();
                await peers.p2.focus();

                await peers.p1.openDataChannel(peers.p2);

                await peers.p1.wysiwyg.odooEditor.execCommand('insert', 'b');

                assert.equal(await peers.p1.getValue(), `<p>ab[]</p>`, 'p1 should have the same document as p2');
                assert.equal(await peers.p2.getValue(), `<p>[]ab</p>`, 'p2 should have the same document as p1');
                assert.equal(await peers.p3.getValue(), `<p>a[]</p>`, 'p3 should not have the document changed');

                removePeers(peers);
            });
            QUnit.test('Focused client should receive step while unfocused should not (if the datachannel is open after the step)', async (assert) => {
                assert.expect(3);
                const pool = await createPeers(['p1', 'p2', 'p3']);
                const peers = pool.peers;

                await peers.p1.startEditor();
                await peers.p2.startEditor();
                await peers.p3.startEditor();

                await peers.p1.focus();
                await peers.p2.focus();

                await peers.p1.wysiwyg.odooEditor.execCommand('insert', 'b');

                await peers.p1.openDataChannel(peers.p2);

                assert.equal(await peers.p1.getValue(), `<p>ab[]</p>`, 'p1 should have the same document as p2');
                assert.equal(await peers.p2.getValue(), `[]<p>ab</p>`, 'p2 should have the same document as p1');
                assert.equal(await peers.p3.getValue(), `<p>a[]</p>`, 'p3 should not have the document changed because it has not focused');

                removePeers(peers);
            });
        });

        QUnit.module('Stale detection & recovery', {}, () => {
            QUnit.module('detect stale while unfocused', async () => {
                QUnit.test('should do nothing until focus', async (assert) => {
                    assert.expect(10);
                    const pool = await createPeers(['p1', 'p2', 'p3']);
                    const peers = pool.peers;

                    await peers.p1.startEditor();
                    await peers.p2.startEditor();
                    await peers.p3.startEditor();

                    await peers.p1.focus();
                    await peers.p2.focus();
                    await peers.p1.openDataChannel(peers.p2);

                    await peers.p1.wysiwyg.odooEditor.execCommand('insert', 'b');
                    await peers.p1.writeToServer();

                    assert.equal(peers.p1.wysiwyg._isDocumentStale, false, 'p1 should not have a stale document');
                    assert.equal(await peers.p1.getValue(), `<p>ab[]</p>`, 'p1 should have the same document as p2');

                    assert.equal(peers.p2.wysiwyg._isDocumentStale, false, 'p2 should not have a stale document');
                    assert.equal(await peers.p2.getValue(), `<p>[]ab</p>`, 'p2 should have the same document as p1');

                    assert.equal(peers.p3.wysiwyg._isDocumentStale, true, 'p3 should have a stale document');
                    assert.equal(await peers.p3.getValue(), `<p>a[]</p>`, 'p3 should not have the same document as p1');

                    await peers.p3.focus();
                    await peers.p1.openDataChannel(peers.p3);
                    // This timeout is necessary for the selection to be set
                    await new Promise(resolve => setTimeout(resolve));

                    assert.equal(peers.p3.wysiwyg._isDocumentStale, false, 'p3 should not have a stale document');
                    assert.equal(await peers.p3.getValue(), `<p>[]ab</p>`, 'p3 should have the same document as p1');

                    await peers.p1.wysiwyg.odooEditor.execCommand('insert', 'c');
                    assert.equal(await peers.p1.getValue(), `<p>abc[]</p>`, 'p1 should have the same document as p3');
                    assert.equal(await peers.p3.getValue(), `<p>[]abc</p>`, 'p3 should have the same document as p1');

                    removePeers(peers);
                });
            });
            QUnit.module('detect stale while focused', async () => {
                QUnit.module('recover from missing steps', async () => {
                    QUnit.test('should recover from missing steps', async (assert) => {
                        assert.expect(18);
                        const pool = await createPeers(['p1', 'p2', 'p3']);
                        const peers = pool.peers;

                        await peers.p1.startEditor();
                        await peers.p2.startEditor();
                        await peers.p3.startEditor();

                        await peers.p1.focus();
                        await peers.p2.focus();
                        await peers.p3.focus();
                        await peers.p1.openDataChannel(peers.p2);
                        await peers.p1.openDataChannel(peers.p3);
                        await peers.p2.openDataChannel(peers.p3);

                        const p3Spies = makeSpies(peers.p3.wysiwyg, [
                            '_recoverFromStaleDocument',
                            '_resetFromServerAndResyncWithClients',
                            '_processMissingSteps',
                            '_applySnapshot',
                        ]);


                        assert.equal(peers.p1.wysiwyg._historyShareId, peers.p2.wysiwyg._historyShareId, 'p1 and p2 should have the same _historyShareId');
                        assert.equal(peers.p1.wysiwyg._historyShareId, peers.p3.wysiwyg._historyShareId, 'p1 and p3 should have the same _historyShareId');

                        assert.equal(await peers.p1.getValue(), `<p>a[]</p>`, 'p1 should have the same document as p2');
                        assert.equal(await peers.p2.getValue(), `<p>[]a</p>`, 'p2 should have the same document as p1');
                        assert.equal(await peers.p3.getValue(), `<p>[]a</p>`, 'p3 should have the same document as p1');

                        await peers.p3.setOffline();

                        await peers.p1.wysiwyg.odooEditor.execCommand('insert', 'b');

                        assert.equal(await peers.p1.getValue(), `<p>ab[]</p>`, 'p1 should have the same document as p2');
                        assert.equal(await peers.p2.getValue(), `<p>[]ab</p>`, 'p2 should have the same document as p1');
                        assert.equal(await peers.p3.getValue(), `<p>[]a</p>`, 'p3 should not have the same document as p1');

                        await peers.p1.writeToServer();
                        assert.equal(peers.p1.wysiwyg._isDocumentStale, false, 'p1 should not have a stale document');
                        assert.equal(peers.p2.wysiwyg._isDocumentStale, false, 'p2 should not have a stale document');
                        assert.equal(peers.p3.wysiwyg._isDocumentStale, false, 'p3 should not have a stale document');

                        await peers.p3.setOnline();

                        assert.equal(p3Spies._recoverFromStaleDocument.callCount, 1, 'p3 _recoverFromStaleDocument should have been called once');
                        assert.equal(p3Spies._processMissingSteps.callCount, 1, 'p3 _processMissingSteps should have been called once');
                        assert.equal(p3Spies._applySnapshot.callCount, 0, 'p3 _applySnapshot should not have been called');
                        assert.equal(p3Spies._resetFromServerAndResyncWithClients.callCount, 0, 'p3 _resetFromServerAndResyncWithClients should not have been called');

                        assert.equal(await peers.p1.getValue(), `<p>ab[]</p>`, 'p1 should have the same document as p2');
                        assert.equal(await peers.p2.getValue(), `<p>[]ab</p>`, 'p2 should have the same document as p1');
                        assert.equal(await peers.p3.getValue(), `<p>[]ab</p>`, 'p3 should have the same document as p1');

                        removePeers(peers);
                    });
                });
                QUnit.module('recover from snapshot', async () => {
                    QUnit.test('should wait for all peer to recover from snapshot', async (assert) => {
                        assert.expect(19);
                        const pool = await createPeers(['p1', 'p2', 'p3']);
                        const peers = pool.peers;

                        await peers.p1.startEditor();
                        await peers.p2.startEditor();
                        await peers.p3.startEditor();

                        await peers.p1.focus();
                        await peers.p2.focus();
                        await peers.p3.focus();

                        await peers.p1.openDataChannel(peers.p2);
                        await peers.p1.openDataChannel(peers.p3);
                        await peers.p2.openDataChannel(peers.p3);
                        peers.p2.setOffline();
                        peers.p3.setOffline();

                        const p2Spies = makeSpies(peers.p2.wysiwyg, [
                            '_recoverFromStaleDocument',
                            '_resetFromServerAndResyncWithClients',
                            '_processMissingSteps',
                            '_applySnapshot',
                        ]);
                        const p3Spies = makeSpies(peers.p3.wysiwyg, [
                            '_recoverFromStaleDocument',
                            '_resetFromServerAndResyncWithClients',
                            '_processMissingSteps',
                            '_applySnapshot',
                            '_onRecoveryClientTimeout',
                        ]);

                        await peers.p1.wysiwyg.odooEditor.execCommand('insert', 'b');
                        await peers.p1.writeToServer();

                        assert.equal(await peers.p1.getValue(), `<p>ab[]</p>`, 'p1 have inserted char b');
                        assert.equal(await peers.p2.getValue(), `<p>[]a</p>`, 'p2 should not have the same document as p1');
                        assert.equal(await peers.p3.getValue(), `<p>[]a</p>`, 'p3 should not have the same document as p1');

                        peers.p1.destroyEditor();

                        assert.equal(p2Spies._recoverFromStaleDocument.callCount, 0, 'p2 _recoverFromStaleDocument should not have been called');
                        assert.equal(p2Spies._resetFromServerAndResyncWithClients.callCount, 0, 'p2 _resetFromServerAndResyncWithClients should not have been called');
                        assert.equal(p2Spies._processMissingSteps.callCount, 0, 'p2 _processMissingSteps should not have been called');
                        assert.equal(p2Spies._applySnapshot.callCount, 0, 'p2 _applySnapshot should not have been called');

                        await peers.p2.setOnline();
                        assert.equal(await peers.p2.getValue(), `[]<p>ab</p>`, 'p2 should have the same document as p1');
                        assert.equal(await peers.p3.getValue(), `<p>[]a</p>`, 'p3 should not have the same document as p1');

                        assert.equal(p2Spies._recoverFromStaleDocument.callCount, 1, 'p2 _recoverFromStaleDocument should have been called once');
                        assert.equal(p2Spies._resetFromServerAndResyncWithClients.callCount, 1, 'p2 _resetFromServerAndResyncWithClients should have been called once');
                        assert.equal(p2Spies._processMissingSteps.callCount, 0, 'p2 _processMissingSteps should not have been called');
                        assert.equal(p2Spies._applySnapshot.callCount, 0, 'p2 _applySnapshot should not have been called');

                        await peers.p3.setOnline();
                        assert.equal(await peers.p3.getValue(), `[]<p>ab</p>`, 'p3 should have the same document as p1');
                        assert.equal(p3Spies._recoverFromStaleDocument.callCount, 1, 'p3 _recoverFromStaleDocument should have been called once');
                        assert.equal(p3Spies._resetFromServerAndResyncWithClients.callCount, 0, 'p3 _resetFromServerAndResyncWithClients should not have been called');
                        assert.equal(p3Spies._processMissingSteps.callCount, 1, 'p3 _processMissingSteps should have been called once');
                        assert.equal(p3Spies._applySnapshot.callCount, 1, 'p3 _applySnapshot should have been called once');
                        assert.equal(p3Spies._onRecoveryClientTimeout.callCount, 0, 'p3 _onRecoveryClientTimeout should not have been called');

                        removePeers(peers);
                    });
                    QUnit.test('should recover from snapshot after PTP_MAX_RECOVERY_TIME if some peer do not respond', async (assert) => {
                        assert.expect(19);
                        const pool = await createPeers(['p1', 'p2', 'p3']);
                        const peers = pool.peers;

                        await peers.p1.startEditor();
                        await peers.p2.startEditor();
                        await peers.p3.startEditor();

                        await peers.p1.focus();
                        await peers.p2.focus();
                        await peers.p3.focus();

                        await peers.p1.openDataChannel(peers.p2);
                        await peers.p1.openDataChannel(peers.p3);
                        await peers.p2.openDataChannel(peers.p3);
                        peers.p2.setOffline();
                        peers.p3.setOffline();

                        const p2Spies = makeSpies(peers.p2.wysiwyg, [
                            '_recoverFromStaleDocument',
                            '_resetFromServerAndResyncWithClients',
                            '_processMissingSteps',
                            '_applySnapshot',
                        ]);
                        const p3Spies = makeSpies(peers.p3.wysiwyg, [
                            '_recoverFromStaleDocument',
                            '_resetFromServerAndResyncWithClients',
                            '_processMissingSteps',
                            '_applySnapshot',
                            '_onRecoveryClientTimeout',
                        ]);

                        await peers.p1.wysiwyg.odooEditor.execCommand('insert', 'b');
                        await peers.p1.writeToServer();
                        peers.p1.setOffline();

                        assert.equal(await peers.p1.getValue(), `<p>ab[]</p>`, 'p1 have inserted char b');
                        assert.equal(await peers.p2.getValue(), `<p>[]a</p>`, 'p2 should not have the same document as p1');
                        assert.equal(await peers.p3.getValue(), `<p>[]a</p>`, 'p3 should not have the same document as p1');

                        assert.equal(p2Spies._recoverFromStaleDocument.callCount, 0, 'p2 _recoverFromStaleDocument should not have been called');
                        assert.equal(p2Spies._resetFromServerAndResyncWithClients.callCount, 0, 'p2 _resetFromServerAndResyncWithClients should not have been called');
                        assert.equal(p2Spies._processMissingSteps.callCount, 0, 'p2 _processMissingSteps should not have been called');
                        assert.equal(p2Spies._applySnapshot.callCount, 0, 'p2 _applySnapshot should not have been called');

                        await peers.p2.setOnline();
                        assert.equal(await peers.p2.getValue(), `[]<p>ab</p>`, 'p2 should have the same document as p1');
                        assert.equal(await peers.p3.getValue(), `<p>[]a</p>`, 'p3 should not have the same document as p1');

                        assert.equal(p2Spies._recoverFromStaleDocument.callCount, 1, 'p2 _recoverFromStaleDocument should have been called once');
                        assert.equal(p2Spies._resetFromServerAndResyncWithClients.callCount, 1, 'p2 _resetFromServerAndResyncWithClients should have been called once');
                        assert.equal(p2Spies._processMissingSteps.callCount, 0, 'p2 _processMissingSteps should not have been called');
                        assert.equal(p2Spies._applySnapshot.callCount, 0, 'p2 _applySnapshot should not have been called');

                        await peers.p3.setOnline();
                        assert.equal(await peers.p3.getValue(), `[]<p>ab</p>`, 'p3 should have the same document as p1');
                        assert.equal(p3Spies._recoverFromStaleDocument.callCount, 1, 'p3 _recoverFromStaleDocument should have been called once');
                        assert.equal(p3Spies._resetFromServerAndResyncWithClients.callCount, 0, 'p3 _resetFromServerAndResyncWithClients should have been called once');
                        assert.equal(p3Spies._processMissingSteps.callCount, 1, 'p3 _processMissingSteps should have been called once');
                        assert.equal(p3Spies._applySnapshot.callCount, 1, 'p3 _applySnapshot should have been called once');
                        assert.equal(p3Spies._onRecoveryClientTimeout.callCount, 1, 'p3 _onRecoveryClientTimeout should have been called once');

                        removePeers(peers);
                    });
                });
                QUnit.module('recover from server', async () => {
                    QUnit.test('should recover from server if no snapshot have been processed', async (assert) => {
                        assert.expect(16);
                        const pool = await createPeers(['p1', 'p2', 'p3']);
                        const peers = pool.peers;

                        await peers.p1.startEditor();
                        await peers.p2.startEditor();
                        await peers.p3.startEditor();

                        await peers.p1.focus();
                        await peers.p2.focus();
                        await peers.p3.focus();

                        await peers.p1.openDataChannel(peers.p2);
                        await peers.p1.openDataChannel(peers.p3);
                        await peers.p2.openDataChannel(peers.p3);
                        peers.p2.setOffline();
                        peers.p3.setOffline();

                        const p2Spies = makeSpies(peers.p2.wysiwyg, [
                            '_recoverFromStaleDocument',
                            '_resetFromServerAndResyncWithClients',
                            '_processMissingSteps',
                            '_applySnapshot',
                            '_onRecoveryClientTimeout',
                            '_resetFromClient',
                        ]);

                        const p3Spies = makeSpies(peers.p3.wysiwyg, [
                            '_recoverFromStaleDocument',
                            '_resetFromServerAndResyncWithClients',
                            '_processMissingSteps',
                            '_applySnapshot',
                            '_onRecoveryClientTimeout',
                            '_resetFromClient',
                        ]);

                        await peers.p1.wysiwyg.odooEditor.execCommand('insert', 'b');
                        await peers.p1.writeToServer();

                        assert.equal(await peers.p1.getValue(), `<p>ab[]</p>`, 'p1 have inserted char b');
                        assert.equal(await peers.p2.getValue(), `<p>[]a</p>`, 'p2 should not have the same document as p1');
                        assert.equal(await peers.p3.getValue(), `<p>[]a</p>`, 'p3 should not have the same document as p1');

                        peers.p1.destroyEditor();

                        assert.equal(p2Spies._recoverFromStaleDocument.callCount, 0, 'p2 _recoverFromStaleDocument should not have been called');
                        assert.equal(p2Spies._resetFromServerAndResyncWithClients.callCount, 0, 'p2 _resetFromServerAndResyncWithClients should not have been called');
                        assert.equal(p2Spies._processMissingSteps.callCount, 0, 'p2 _processMissingSteps should not have been called');
                        assert.equal(p2Spies._applySnapshot.callCount, 0, 'p2 _applySnapshot should not have been called');
                        assert.equal(p2Spies._onRecoveryClientTimeout.callCount, 0, 'p2 _onRecoveryClientTimeout should not have been called');
                        assert.equal(p2Spies._resetFromClient.callCount, 0, 'p2 _resetFromClient should not have been called');

                        // Because we do not wait for the end of the
                        // p2.setOnline promise, p3 will not be able to reset
                        // from p2 wich allow us to test that p3 reset from the
                        // server as a fallback.
                        peers.p2.setOnline();
                        await peers.p3.setOnline();

                        assert.equal(await peers.p3.getValue(), `[]<p>ab</p>`, 'p3 should have the same document as p1');

                        assert.equal(p3Spies._recoverFromStaleDocument.callCount, 1, 'p3 _recoverFromStaleDocument should have been called once');
                        assert.equal(p3Spies._resetFromServerAndResyncWithClients.callCount, 1, 'p3 _resetFromServerAndResyncWithClients should have been called once');
                        assert.equal(p3Spies._processMissingSteps.callCount, 0, 'p3 _processMissingSteps should not have been called');
                        assert.equal(p3Spies._applySnapshot.callCount, 1, 'p3 _applySnapshot should have been called once');
                        assert.equal(p3Spies._onRecoveryClientTimeout.callCount, 0, 'p3 _onRecoveryClientTimeout should not have been called');
                        assert.equal(p3Spies._resetFromClient.callCount, 1, 'p3 _resetFromClient should have been called once');

                        removePeers(peers);
                    });
                    QUnit.test('should recover from server if there is no peer connected', async (assert) => {
                        assert.expect(14);
                        const pool = await createPeers(['p1', 'p2']);
                        const peers = pool.peers;

                        await peers.p1.startEditor();
                        await peers.p2.startEditor();

                        await peers.p1.focus();
                        await peers.p2.focus();

                        await peers.p1.openDataChannel(peers.p2);
                        peers.p2.setOffline();

                        const p2Spies = makeSpies(peers.p2.wysiwyg, [
                            '_recoverFromStaleDocument',
                            '_resetFromServerAndResyncWithClients',
                            '_processMissingSteps',
                            '_applySnapshot',
                            '_onRecoveryClientTimeout',
                            '_resetFromClient',
                        ]);

                        await peers.p1.wysiwyg.odooEditor.execCommand('insert', 'b');
                        await peers.p1.writeToServer();

                        assert.equal(await peers.p1.getValue(), `<p>ab[]</p>`, 'p1 have inserted char b');
                        assert.equal(await peers.p2.getValue(), `[]<p>a</p>`, 'p2 should not have the same document as p1');

                        peers.p1.destroyEditor();

                        assert.equal(p2Spies._recoverFromStaleDocument.callCount, 0, 'p2 _recoverFromStaleDocument should not have been called');
                        assert.equal(p2Spies._resetFromServerAndResyncWithClients.callCount, 0, 'p2 _resetFromServerAndResyncWithClients should not have been called');
                        assert.equal(p2Spies._processMissingSteps.callCount, 0, 'p2 _processMissingSteps should not have been called');
                        assert.equal(p2Spies._applySnapshot.callCount, 0, 'p2 _applySnapshot should not have been called');
                        assert.equal(p2Spies._resetFromClient.callCount, 0, 'p2 _resetFromClient should not have been called');

                        await peers.p2.setOnline();
                        assert.equal(await peers.p2.getValue(), `[]<p>ab</p>`, 'p2 should have the same document as p1');

                        assert.equal(p2Spies._recoverFromStaleDocument.callCount, 1, 'p2 _recoverFromStaleDocument should have been called once');
                        assert.equal(p2Spies._resetFromServerAndResyncWithClients.callCount, 1, 'p2 _resetFromServerAndResyncWithClients should have been called once');
                        assert.equal(p2Spies._processMissingSteps.callCount, 0, 'p2 _processMissingSteps should not have been called');
                        assert.equal(p2Spies._applySnapshot.callCount, 0, 'p2 _applySnapshot should not have been called');
                        assert.equal(p2Spies._onRecoveryClientTimeout.callCount, 0, 'p2 _onRecoveryClientTimeout should not have been called');
                        assert.equal(p2Spies._resetFromClient.callCount, 0, 'p2 _resetFromClient should not have been called');

                        removePeers(peers);
                    });
                    QUnit.test('should recover from server if there is no response after PTP_MAX_RECOVERY_TIME', async (assert) => {
                        assert.expect(16);
                        const pool = await createPeers(['p1', 'p2', 'p3']);
                        const peers = pool.peers;

                        await peers.p1.startEditor();
                        await peers.p2.startEditor();
                        await peers.p3.startEditor();

                        await peers.p1.focus();
                        await peers.p2.focus();

                        await peers.p1.openDataChannel(peers.p2);
                        await peers.p1.openDataChannel(peers.p3);
                        await peers.p2.openDataChannel(peers.p3);
                        peers.p2.setOffline();
                        peers.p3.setOffline();

                        const p2Spies = makeSpies(peers.p2.wysiwyg, [
                            '_recoverFromStaleDocument',
                            '_resetFromServerAndResyncWithClients',
                            '_processMissingSteps',
                            '_applySnapshot',
                            '_onRecoveryClientTimeout',
                            '_resetFromClient',
                        ]);

                        await peers.p1.wysiwyg.odooEditor.execCommand('insert', 'b');
                        await peers.p1.writeToServer();
                        peers.p1.setOffline();

                        assert.equal(await peers.p1.getValue(), `<p>ab[]</p>`, 'p1 have inserted char b');
                        assert.equal(await peers.p2.getValue(), `<p>[]a</p>`, 'p2 should not have the same document as p1');
                        assert.equal(await peers.p3.getValue(), `<p>[]a</p>`, 'p3 should not have the same document as p1');

                        assert.equal(p2Spies._recoverFromStaleDocument.callCount, 0, 'p2 _recoverFromStaleDocument should not have been called');
                        assert.equal(p2Spies._resetFromServerAndResyncWithClients.callCount, 0, 'p2 _resetFromServerAndResyncWithClients should not have been called');
                        assert.equal(p2Spies._processMissingSteps.callCount, 0, 'p2 _processMissingSteps should not have been called');
                        assert.equal(p2Spies._applySnapshot.callCount, 0, 'p2 _applySnapshot should not have been called');
                        assert.equal(p2Spies._resetFromClient.callCount, 0, 'p2 _resetFromClient should not have been called');

                        await peers.p2.setOnline();
                        assert.equal(await peers.p2.getValue(), `[]<p>ab</p>`, 'p2 should have the same document as p1');
                        assert.equal(await peers.p3.getValue(), `<p>[]a</p>`, 'p3 should not have the same document as p1');

                        assert.equal(p2Spies._recoverFromStaleDocument.callCount, 1, 'p2 _recoverFromStaleDocument should have been called once');
                        assert.equal(p2Spies._resetFromServerAndResyncWithClients.callCount, 1, 'p2 _resetFromServerAndResyncWithClients should have been called once');
                        assert.equal(p2Spies._processMissingSteps.callCount, 0, 'p2 _processMissingSteps should not have been called');
                        assert.equal(p2Spies._applySnapshot.callCount, 0, 'p2 _applySnapshot should not have been called');
                        assert.equal(p2Spies._onRecoveryClientTimeout.callCount, 1, 'p2 _onRecoveryClientTimeout should have been called once');
                        // p1 and p3 are considered offline but not
                        // disconnected. It means that p2 will try to recover
                        // from p1 and p3 even if they are currently
                        // unavailable. This test is usefull to check that the
                        // code path to _resetFromClient is properly taken.
                        assert.equal(p2Spies._resetFromClient.callCount, 2, 'p2 _resetFromClient should have been called twice');

                        removePeers(peers);
                    });
                });
            });
        });
        QUnit.module('Disconnect & reconnect', {}, () => {
            QUnit.test('should sync history when disconnecting and reconnecting to internet', async (assert) => {
                assert.expect(2);
                const pool = await createPeers(['p1', 'p2']);
                const peers = pool.peers;

                await peers.p1.startEditor();
                await peers.p2.startEditor();

                await peers.p1.focus();
                await peers.p2.focus();
                await peers.p1.openDataChannel(peers.p2);

                await peers.p1.wysiwyg.odooEditor.execCommand('insert', 'b');

                await peers.p1.setOffline();
                peers.p1.removeDataChannel(peers.p2);

                const setSelection = peer => {
                    const selection = peer.document.getSelection();
                    const pElement = peer.wysiwyg.odooEditor.editable.querySelector('p')
                    const range = new Range();
                    range.setStart(pElement, 1);
                    range.setEnd(pElement, 1);
                    selection.removeAllRanges();
                    selection.addRange(range);
                }
                const addP = (peer, content) => {
                    const p = document.createElement('p');
                    p.textContent = content;
                    peer.wysiwyg.odooEditor.editable.append(p);
                    peer.wysiwyg.odooEditor.historyStep();
                }

                setSelection(peers.p1);
                await peers.p1.wysiwyg.odooEditor.execCommand('insert', 'c');
                addP(peers.p1, 'd');

                setSelection(peers.p2);
                await peers.p2.wysiwyg.odooEditor.execCommand('insert', 'e');
                addP(peers.p2, 'f');

                peers.p1.setOnline();
                peers.p2.setOnline();

                // todo: p1PromiseForMissingStep and p2PromiseForMissingStep
                // should be removed when the fix of undetected missing step
                // will be merged. (task-3208277)
                const p1PromiseForMissingStep = new Promise((resolve) => {
                    patch(peers.p2.wysiwyg, {
                        async _processMissingSteps() {
                            // Wait for the p2PromiseForMissingStep to resolve
                            // to avoid undetected missing step.
                            await p2PromiseForMissingStep;
                            super._processMissingSteps(...arguments);
                            resolve();
                        }
                    })
                });
                const p2PromiseForMissingStep = new Promise((resolve) => {
                    patch(peers.p1.wysiwyg, {
                        async _processMissingSteps() {
                            super._processMissingSteps(...arguments);
                            resolve();
                        }
                    })
                });

                await peers.p1.openDataChannel(peers.p2);
                await p1PromiseForMissingStep;

                assert.equal(await peers.p1.getValue(), `<p>ac[]eb</p><p>d</p><p>f</p>`, 'p1 should have the value merged with p2');
                assert.equal(await peers.p2.getValue(), `<p>ace[]b</p><p>d</p><p>f</p>`, 'p2 should have the value merged with p1');

                removePeers(peers);
            });
        });
    });
});


