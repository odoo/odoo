/** @odoo-module **/

import { patch, unpatch } from "@web/core/utils/patch";
import {
    parseTextualSelection,
    setTestSelection,
    renderTextualSelection,
    patchEditorIframe,
} from '@web_editor/js/editor/odoo-editor/test/utils';
import { stripHistoryIds } from '@web_editor/js/backend/html_field';
import Wysiwyg from 'web_editor.wysiwyg';
import { Mutex } from '@web/core/utils/concurrency';

function makeSpy() {
    const spy = function() {
        spy.callCount++;
        return this._super.apply(this, arguments);
    };
    spy.callCount = 0;
    return spy;
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
        this._started = this.wysiwyg.appendTo(this.wrapper);
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

async function createPeers(peers) {
    const pool = new PeerPool();

    let lastGeneratedId = 0;

    for (const peerId of peers) {
        const peerWysiwygWrapper = document.createElement('div');
        peerWysiwygWrapper.classList.add('peer_wysiwyg_wrapper');
        peerWysiwygWrapper.classList.add('client_' + peerId);

        const iframe = document.createElement('iframe');
        if (navigator.userAgent.toLowerCase().indexOf('firefox') > -1) {
            // Firefox reset the page without this hack.
            // With this hack, chrome does not render content.
            iframe.setAttribute('src', ' javascript:void(0);');
        }
        document.querySelector('#qunit-fixture').append(iframe);
        patchEditorIframe(iframe);
        iframe.contentDocument.body.append(peerWysiwygWrapper);
        iframe.contentWindow.$ = $;

        const fakeWysiwygParent = {
            _trigger_up: () => {},
        };

        const wysiwyg = new Wysiwyg(fakeWysiwygParent, {
            value: initialValue,
            collaborative: true,
            collaborationChannel: {
                collaborationFieldName: "fake_field",
                collaborationModelName: "fake.model",
                collaborationResId: 1
            },
            document: iframe.contentWindow.document,
        });
        patch(wysiwyg, 'web_editor', {
            _generateClientId() {
                return peerId;
            },
            // Hacky hook as we know this method is called after setting the value in the wysiwyg start and before sending the value to odooEditor.
            _getLastHistoryStepId() {
                pool.peers[peerId].initialParsedSelection = parseTextualSelection(wysiwyg.$editable[0]);
                return this._super(...arguments);
            },
            call: () => {},
            getSession: () => ({notification_type: true}),
            _rpc(params) {
                if (params.route === '/web_editor/get_ice_servers') {
                    return [];
                } else if (params.route === '/web_editor/bus_broadcast') {
                    const currentPeer = pool.peers[peerId];
                    for (const peer of currentPeer._connections) {
                        peer.wysiwyg.ptp.handleNotification(structuredClone(params.params.bus_data));
                    }
                } else if (params.model === "res.users" && params.method === "search_read") {
                    return [{ name: "admin" }];
                }
            },
            _getNewPtp() {
                const ptp = this._super(...arguments);
                ptp.options.onRequest.get_client_avatar = () => '';

                patch(ptp, "web_editor_peer_to_peer", {
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
                        this._super(...args);
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
                await this._super(...arguments);
                patch(this.odooEditor, 'odooEditor', {
                    _generateId() {
                        // Ensure the id are deterministically gererated for
                        // when we need to sort by them. (eg. in the
                        // callaboration sorting of steps)
                        lastGeneratedId++;
                        return lastGeneratedId.toString();
                    },
                });
            }
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
function removePeers(peers) {
    for (const peer of Object.values(peers)) {
        peer.wysiwyg.destroy();
        peer.wrapper.remove();
    }
}

QUnit.module('web_editor', {
    before() {
        patch(Wysiwyg, 'web_editor', {
            activeCollaborationChannelNames: {
                has: () => false,
                add: () => {},
                delete: () => {},
            }
        });
    },
    after() {
        unpatch(Wysiwyg, "web_editor");
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

                        const p3Spies = {
                            _recoverFromStaleDocument: makeSpy(),
                            _resetFromServerAndResyncWithClients: makeSpy(),
                            _processMissingSteps: makeSpy(),
                            _applySnapshot: makeSpy(),
                        };
                        patch(peers.p3.wysiwyg, 'test', p3Spies);

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
                        unpatch(peers.p3.wysiwyg, 'test');

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

                        const p2Spies = {
                            _recoverFromStaleDocument: makeSpy(),
                            _resetFromServerAndResyncWithClients: makeSpy(),
                            _processMissingSteps: makeSpy(),
                            _applySnapshot: makeSpy(),
                        };
                        patch(peers.p2.wysiwyg, 'test', p2Spies);
                        const p3Spies = {
                            _recoverFromStaleDocument: makeSpy(),
                            _resetFromServerAndResyncWithClients: makeSpy(),
                            _processMissingSteps: makeSpy(),
                            _applySnapshot: makeSpy(),
                            _onRecoveryClientTimeout: makeSpy(),
                        };
                        patch(peers.p3.wysiwyg, 'test', p3Spies);

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

                        unpatch(peers.p2.wysiwyg, 'test');
                        unpatch(peers.p3.wysiwyg, 'test');

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

                        const p2Spies = {
                            _recoverFromStaleDocument: makeSpy(),
                            _resetFromServerAndResyncWithClients: makeSpy(),
                            _processMissingSteps: makeSpy(),
                            _applySnapshot: makeSpy(),
                        };
                        patch(peers.p2.wysiwyg, 'test', p2Spies);
                        const p3Spies = {
                            _recoverFromStaleDocument: makeSpy(),
                            _resetFromServerAndResyncWithClients: makeSpy(),
                            _processMissingSteps: makeSpy(),
                            _applySnapshot: makeSpy(),
                            _onRecoveryClientTimeout: makeSpy(),
                        };
                        patch(peers.p3.wysiwyg, 'test', p3Spies);

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

                        unpatch(peers.p2.wysiwyg, 'test');
                        unpatch(peers.p3.wysiwyg, 'test');

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

                        const p2Spies = {
                            _recoverFromStaleDocument: makeSpy(),
                            _resetFromServerAndResyncWithClients: makeSpy(),
                            _processMissingSteps: makeSpy(),
                            _applySnapshot: makeSpy(),
                            _onRecoveryClientTimeout: makeSpy(),
                            _resetFromClient: makeSpy(),
                        };

                        patch(peers.p2.wysiwyg, 'test', p2Spies);
                        const p3Spies = {
                            _recoverFromStaleDocument: makeSpy(),
                            _resetFromServerAndResyncWithClients: makeSpy(),
                            _processMissingSteps: makeSpy(),
                            _applySnapshot: makeSpy(),
                            _onRecoveryClientTimeout: makeSpy(),
                            _resetFromClient: makeSpy(),
                        };
                        patch(peers.p3.wysiwyg, 'test', p3Spies);

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

                        unpatch(peers.p2.wysiwyg, 'test');
                        unpatch(peers.p3.wysiwyg, 'test');

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

                        const p2Spies = {
                            _recoverFromStaleDocument: makeSpy(),
                            _resetFromServerAndResyncWithClients: makeSpy(),
                            _processMissingSteps: makeSpy(),
                            _applySnapshot: makeSpy(),
                            _onRecoveryClientTimeout: makeSpy(),
                            _resetFromClient: makeSpy(),
                        };
                        patch(peers.p2.wysiwyg, 'test', p2Spies);

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

                        unpatch(peers.p2.wysiwyg, 'test');

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

                        const p2Spies = {
                            _recoverFromStaleDocument: makeSpy(),
                            _resetFromServerAndResyncWithClients: makeSpy(),
                            _processMissingSteps: makeSpy(),
                            _applySnapshot: makeSpy(),
                            _onRecoveryClientTimeout: makeSpy(),
                            _resetFromClient: makeSpy(),
                        };
                        patch(peers.p2.wysiwyg, 'test', p2Spies);

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

                        unpatch(peers.p2.wysiwyg, 'test');

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
                    patch(peers.p2.wysiwyg, 'missingSteps', {
                        async _processMissingSteps() {
                            const _super = this._super;
                            // Wait for the p2PromiseForMissingStep to resolve
                            // to avoid undetected missing step.
                            await p2PromiseForMissingStep;
                            _super(...arguments);
                            resolve();
                        }
                    })
                });
                const p2PromiseForMissingStep = new Promise((resolve) => {
                    patch(peers.p1.wysiwyg, 'missingSteps', {
                        async _processMissingSteps() {
                            this._super(...arguments);
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


