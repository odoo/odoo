/** @odoo-module */

import { stripHistoryIds } from "@html_editor/others/collaboration/collaboration_odoo_plugin";
import { HISTORY_SNAPSHOT_INTERVAL } from "@html_editor/others/collaboration/collaboration_plugin";
import { COLLABORATION_PLUGINS, MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { Wysiwyg } from "@html_editor/wysiwyg";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { Mutex } from "@web/core/utils/concurrency";
import { normalizeHTML } from "@html_editor/utils/html";
import { patch } from "@web/core/utils/patch";
import { getContent, getSelection, setSelection } from "./_helpers/selection";
import { insertText } from "./_helpers/user_actions";
import { animationFrame, advanceTime } from "@odoo/hoot-mock";
import { waitUntil } from "@odoo/hoot-dom";

/**
 * @typedef PeerPool
 * @property {Record<string, PeerTest>} peers
 * @property {string} lastRecordSaved
 */

function makeSpy(obj, functionName) {
    const spy = {
        callCount: 0,
    };
    patch(obj, {
        [functionName]() {
            spy.callCount++;
            return super[functionName].apply(this, arguments);
        },
    });
    return spy;
}
function makeSpies(obj, methodNames) {
    const methods = {};
    for (const methodName of methodNames) {
        methods[methodName] = makeSpy(obj, methodName);
    }
    return methods;
}

class PeerTest {
    constructor() {
        this.connections = new Set();
        this.onlineMutex = new Mutex();
        this.isOnline = true;
    }
    setInfos(infos) {
        this.peerId = infos.peerId;
        this.editor = infos.editor;
        this.plugins = infos.plugins;
        this.pool = infos.pool;
        this.peers = infos.pool.peers;
        this.document = this.editor.document;
    }
    async destroyEditor() {
        for (const peer of this.connections) {
            peer.connections.delete(this);
        }
        this.editor.destroy();
    }
    async focus() {
        return this.plugins["collaborationOdoo"].joinPeerToPeer();
    }
    async openDataChannel(peer) {
        this.connections.add(peer);
        peer.connections.add(this);
        const ptpFrom = this.ptp;
        const ptpTo = peer.ptp;
        ptpFrom.peersInfos[peer.peerId] ||= {};
        ptpTo.peersInfos[this.peerId] ||= {};

        // Simulate the rtc_data_channel_open on both peers.
        await this.ptp.notifySelf("rtc_data_channel_open", {
            connectionPeerId: peer.peerId,
        });
        await peer.ptp.notifySelf("rtc_data_channel_open", {
            connectionPeerId: this.peerId,
        });
    }
    getValue() {
        const content = getContent(this.editor.editable);
        return normalizeHTML(content, stripHistoryIds);
    }
    async writeToServer() {
        this.pool.lastRecordSaved = this.editor.getContent();
        const lastId = this.plugins.collaborationOdoo.getLastHistoryStepId(
            this.pool.lastRecordSaved
        );
        for (const peer of Object.values(this.peers)) {
            if (peer === this) {
                continue;
            }
            peer.onlineMutex.exec(async () => {
                return peer.plugins.collaborationOdoo.onServerLastIdUpdate(String(lastId));
            });
        }
    }
    async setOnline() {
        this.isOnline = true;
        this.onlineResolver && this.onlineResolver();
        return this.onlineMutex.getUnlockedDef();
    }
    setOffline() {
        this.isOnline = false;
        if (this.onlineResolver) {
            return;
        }
        this.onlineMutex.exec(async () => {
            await new Promise((resolve) => {
                this.onlineResolver = () => {
                    this.onlineResolver = null;
                    resolve();
                };
            });
        });
    }
}

const initialValue = '<p data-last-history-steps="1">a[]</p>';

class Wysiwygs extends Component {
    static template = xml`
        <div>
            <t t-foreach="this.props.peerIds" t-as="peerId" t-key="peerId">
                <Wysiwyg
                    config="getConfig({peerId})"
                    t-key="peerId"
                    iframe="true"
                    onLoad="(editor) => this.onLoad(peerId, editor)"
                    />
            </t>
        </div>
    `;
    static components = { Wysiwyg };
    static props = {
        peerIds: Array,
        pool: Object,
    };
    setup() {
        this.peerResolvers = {};
        this.peerPromises = Promise.all(
            this.props.peerIds.map((peerId) => {
                return new Promise((resolve) => {
                    this.peerResolvers[peerId] = resolve;
                });
            })
        );
        this.loadedPromise = new Promise((resolve) => {
            this.loadedResolver = resolve;
        });
        this.lastStepId = 0;
    }
    getConfig({ peerId }) {
        const busService = {
            subscribe() {},
            unsubscribe() {},
            addEventListener: () => {},
            removeEventListener: () => {},
            addChannel: () => {},
            deleteChannel: () => {},
        };
        return {
            Plugins: [...MAIN_PLUGINS, ...COLLABORATION_PLUGINS],
            content: initialValue.replaceAll("[]", ""),
            collaboration: {
                peerId,
                busService,
                collaborationChannel: {
                    collaborationFieldName: "fake_field",
                    collaborationModelName: "fake.model",
                    collaborationResId: 1,
                },
                collaborativeTrigger: "focus",
            },
        };
    }
    onLoad(peerId, editor) {
        const oldAttach = editor.attachTo.bind(editor);
        const loadedResolver = this.peerResolvers[peerId];
        const startPlugins = editor.startPlugins.bind(editor);
        editor.startPlugins = () => {
            const plugins = Object.fromEntries(editor.plugins.map((p) => [p.constructor.id, p]));
            const { pool } = this.props;
            const { peers } = this.props.pool;

            patch(plugins["collaborationOdoo"], {
                getMetadata() {
                    const result = super.getMetadata();
                    result.avatarUrl = ``;
                    return result;
                },
                getNewPtp() {
                    this.startCollaborationTime = parseInt(peerId.match(/\d+/));
                    const ptp = super.getNewPtp();
                    peers[peerId].ptp = ptp;
                    const broadcastAll = (params) => {
                        for (const peer of peers[peerId].connections) {
                            peer.ptp.handleNotification(structuredClone(params));
                        }
                    };
                    patch(ptp, {
                        removePeer(peerId) {
                            this.notifySelf("ptp_remove", peerId);
                            delete this.peersInfos[peerId];
                        },
                        notifyAllPeers(...args) {
                            // This is not needed because the opening of the
                            // dataChannel is done through `openDataChannel` and we
                            // do not want to simulate the events that thrigger the
                            // openning of the dataChannel.
                            if (args[0] === "ptp_join") {
                                return;
                            }
                            this.options.broadcastAll = broadcastAll;
                            super.notifyAllPeers(...args);
                        },
                        _getPtpPeers() {
                            return peers[peerId].connections.map((peer) => {
                                return { id: peer.peerId };
                            });
                        },
                        async _channelNotify(peerId, transportPayload) {
                            if (
                                !peers[peerId].isOnline ||
                                !peers[transportPayload.fromPeerId].isOnline
                            ) {
                                return;
                            }
                            peers[peerId].ptp.handleNotification(structuredClone(transportPayload));
                        },

                        _createPeer() {
                            throw new Error("Should not be called.");
                        },
                        _addIceCandidate() {
                            throw new Error("Should not be called.");
                        },
                        _recoverConnection() {
                            throw new Error("Should not be called.");
                        },
                        _killPotentialZombie() {
                            throw new Error("Should not be called.");
                        },
                    });

                    loadedResolver();
                    return ptp;
                },
                getCurrentRecord() {
                    return {
                        id: 1,
                        fake_field: pool.lastRecordSaved,
                    };
                },
            });
            patch(plugins["history"], {
                generateId: () => {
                    this.lastStepId++;
                    return this.lastStepId.toString();
                },
            });

            pool.peers[peerId].setInfos({
                peerId,
                pool,
                editor,
                plugins,
            });

            return startPlugins();
        };
        editor.attachTo = (el) => {
            const editable = document.createElement("div");
            el.replaceChildren(editable);

            oldAttach(editable);
            // const configSelection = getSelection(editable, initialValue);
            // if (configSelection) {
            //     editable.focus();
            // }
            setSelection(getSelection(editable, initialValue));
        };
    }
}

async function createPeers(peerIds) {
    /**
     * @type PeerPool
     */
    const pool = {
        peers: Object.fromEntries(peerIds.map((peerId) => [peerId, new PeerTest()])),
        lastRecordSaved: "",
    };

    const wysiwygs = await mountWithCleanup(Wysiwygs, {
        props: {
            peerIds,
            pool,
        },
    });
    await wysiwygs.peerPromises;

    return pool;
}

async function insertEditorText(editor, text) {
    await insertText(editor, text);
    editor.shared.history.addStep();
}

beforeEach(() => {
    onRpc("/web/dataset/call_kw/res.users/read", () => {
        return [{ id: 0, name: "admin" }];
    });
    onRpc("/html_editor/get_ice_servers", () => {
        return [];
    });
    onRpc("/html_editor/bus_broadcast", (params) => {
        throw new Error("Should not be called.");
    });
});

describe("Focus", () => {
    test("Focused peer should not receive step if no data channel is open", async () => {
        const pool = await createPeers(["p1", "p2", "p3"]);
        const peers = pool.peers;

        await peers.p1.focus();
        await peers.p2.focus();

        await insertEditorText(peers.p1.editor, "b");

        expect(peers.p1.getValue()).toBe(`<p>ab[]</p>`, {
            message: "p1 should have the document changed",
        });
        expect(peers.p2.getValue()).toBe(`<p>a[]</p>`, {
            message: "p2 should not have the document changed",
        });
        expect(peers.p3.getValue()).toBe(`<p>a[]</p>`, {
            message: "p3 should not have the document changed",
        });
    });
    test("Focused peer should receive step while unfocused should not (if the datachannel is open before the step)", async () => {
        const pool = await createPeers(["p1", "p2", "p3"]);
        const peers = pool.peers;

        await peers.p1.focus();
        await peers.p2.focus();

        await peers.p1.openDataChannel(peers.p2);

        await insertEditorText(peers.p1.editor, "b");
        await animationFrame();

        expect(peers.p1.getValue()).toBe(`<p>ab[]</p>`, {
            message: "p1 should have the same document as p2",
        });
        expect(peers.p2.getValue()).toBe(`<p>[]ab</p>`, {
            message: "p2 should have the same document as p1",
        });
        expect(peers.p3.getValue()).toBe(`<p>a[]</p>`, {
            message: "p3 should not have the document changed",
        });
    });
    test("Focused peer should receive step while unfocused should not (if the datachannel is open after the step)", async () => {
        const pool = await createPeers(["p1", "p2", "p3"]);
        const peers = pool.peers;

        await peers.p1.focus();
        await peers.p2.focus();

        await insertEditorText(peers.p1.editor, "b");

        await peers.p1.openDataChannel(peers.p2);

        expect(peers.p1.getValue()).toBe(`<p>ab[]</p>`, {
            message: "p1 should have the same document as p2",
        });
        expect(peers.p2.getValue()).toBe(`<p>[]ab</p>`, {
            message: "p2 should have the same document as p1",
        });
        expect(peers.p3.getValue()).toBe(`<p>a[]</p>`, {
            message: "p3 should not have the document changed because it has not focused",
        });
    });
});
describe("Stale detection & recovery", () => {
    describe("detect stale while unfocused", () => {
        test("should do nothing until focus", async () => {
            const pool = await createPeers(["p1", "p2", "p3"]);
            const peers = pool.peers;

            await peers.p1.focus();
            await peers.p2.focus();
            await peers.p1.openDataChannel(peers.p2);

            await insertEditorText(peers.p1.editor, "b");

            await peers.p1.writeToServer();

            expect(peers.p1.plugins.collaborationOdoo.isDocumentStale).toBe(false, {
                message: "p1 should not have a stale document",
            });
            expect(peers.p1.getValue()).toBe(`<p>ab[]</p>`, {
                message: "p1 should have the same document as p2",
            });

            expect(peers.p2.plugins.collaborationOdoo.isDocumentStale).toBe(false, {
                message: "p2 should not have a stale document",
            });
            expect(peers.p2.getValue()).toBe(`<p>[]ab</p>`, {
                message: "p2 should have the same document as p1",
            });

            expect(peers.p3.plugins.collaborationOdoo.isDocumentStale).toBe(true, {
                message: "p3 should have a stale document",
            });
            expect(peers.p3.getValue()).toBe(`<p>a[]</p>`, {
                message: "p3 should not have the same document as p1",
            });

            await peers.p3.focus();
            await peers.p1.openDataChannel(peers.p3);
            // This timeout is necessary for the selection to be set
            await new Promise((resolve) => setTimeout(resolve));

            expect(peers.p3.plugins.collaborationOdoo.isDocumentStale).toBe(false, {
                message: "p3 should not have a stale document",
            });
            expect(peers.p3.getValue()).toBe(`<p>[]ab</p>`, {
                message: "p3 should have the same document as p1",
            });

            await insertEditorText(peers.p1.editor, "c");

            expect(peers.p1.getValue()).toBe(`<p>abc[]</p>`, {
                message: "p1 should have the same document as p3",
            });
            expect(peers.p3.getValue()).toBe(`<p>[]abc</p>`, {
                message: "p3 should have the same document as p1",
            });
        });
    });
    describe("detect stale while focused", () => {
        describe("recover from missing steps", () => {
            test("should recover from missing steps", async () => {
                const pool = await createPeers(["p1", "p2", "p3"]);
                const peers = pool.peers;

                await peers.p1.focus();
                await peers.p2.focus();
                await peers.p3.focus();
                await peers.p1.openDataChannel(peers.p2);
                await peers.p1.openDataChannel(peers.p3);
                await peers.p2.openDataChannel(peers.p3);

                const p3Spies = makeSpies(peers.p3.plugins.collaborationOdoo, [
                    "recoverFromStaleDocument",
                    "resetFromServerAndResyncWithPeers",
                    "processMissingSteps",
                    "applySnapshot",
                ]);

                expect(peers.p1.plugins.collaborationOdoo.historyShareId).toBe(
                    peers.p2.plugins.collaborationOdoo.historyShareId,
                    {
                        message: "p1 and p2 should have the same historyShareId",
                    }
                );
                expect(peers.p1.plugins.collaborationOdoo.historyShareId).toBe(
                    peers.p3.plugins.collaborationOdoo.historyShareId,
                    {
                        message: "p1 and p3 should have the same historyShareId",
                    }
                );

                expect(peers.p1.getValue()).toBe(`<p>a[]</p>`, {
                    message: "p1 should have the same document as p2",
                });
                expect(peers.p2.getValue()).toBe(`<p>[]a</p>`, {
                    message: "p2 should have the same document as p1",
                });
                expect(peers.p3.getValue()).toBe(`<p>[]a</p>`, {
                    message: "p3 should have the same document as p1",
                });

                peers.p3.setOffline();

                await insertEditorText(peers.p1.editor, "b");

                expect(peers.p1.getValue()).toBe(`<p>ab[]</p>`, {
                    message: "p1 should have the same document as p2",
                });
                expect(peers.p2.getValue()).toBe(`<p>[]ab</p>`, {
                    message: "p2 should have the same document as p1",
                });
                expect(peers.p3.getValue()).toBe(`<p>[]a</p>`, {
                    message: "p3 should not have the same document as p1",
                });

                await peers.p1.writeToServer();
                expect(peers.p1.plugins.collaborationOdoo.isDocumentStale).toBe(false, {
                    message: "p1 should not have a stale document",
                });
                expect(peers.p2.plugins.collaborationOdoo.isDocumentStale).toBe(false, {
                    message: "p2 should not have a stale document",
                });
                expect(peers.p3.plugins.collaborationOdoo.isDocumentStale).toBe(false, {
                    message: "p3 should not have a stale document",
                });

                await peers.p3.setOnline();

                expect(p3Spies.recoverFromStaleDocument.callCount).toBe(1, {
                    message: "p3 recoverFromStaleDocument should have been called once",
                });
                expect(p3Spies.processMissingSteps.callCount).toBe(1, {
                    message: "p3 processMissingSteps should have been called once",
                });
                expect(p3Spies.applySnapshot.callCount).toBe(0, {
                    message: "p3 applySnapshot should not have been called",
                });
                expect(p3Spies.resetFromServerAndResyncWithPeers.callCount).toBe(0, {
                    message: "p3 resetFromServerAndResyncWithPeers should not have been called",
                });

                expect(peers.p1.getValue()).toBe(`<p>ab[]</p>`, {
                    message: "p1 should have the same document as p2",
                });
                expect(peers.p2.getValue()).toBe(`<p>[]ab</p>`, {
                    message: "p2 should have the same document as p1",
                });
                expect(peers.p3.getValue()).toBe(`<p>[]ab</p>`, {
                    message: "p3 should have the same document as p1",
                });
            });
        });
        describe("recover from snapshot", () => {
            test("should wait for all peer to recover from snapshot", async () => {
                const pool = await createPeers(["p1", "p2", "p3"]);
                const peers = pool.peers;

                await peers.p1.focus();
                await peers.p2.focus();
                await peers.p3.focus();

                await peers.p1.openDataChannel(peers.p2);
                await peers.p1.openDataChannel(peers.p3);
                await peers.p2.openDataChannel(peers.p3);
                peers.p2.setOffline();
                peers.p3.setOffline();

                const p2Spies = makeSpies(peers.p2.plugins.collaborationOdoo, [
                    "recoverFromStaleDocument",
                    "resetFromServerAndResyncWithPeers",
                    "processMissingSteps",
                    "applySnapshot",
                ]);
                const p3Spies = makeSpies(peers.p3.plugins.collaborationOdoo, [
                    "recoverFromStaleDocument",
                    "resetFromServerAndResyncWithPeers",
                    "processMissingSteps",
                    "applySnapshot",
                    "onRecoveryPeerTimeout",
                ]);

                await insertEditorText(peers.p1.editor, "b");

                await peers.p1.writeToServer();

                expect(peers.p1.getValue()).toBe(`<p>ab[]</p>`, {
                    message: "p1 have inserted char b",
                });
                expect(peers.p2.getValue()).toBe(`<p>[]a</p>`, {
                    message: "p2 should not have the same document as p1",
                });
                expect(peers.p3.getValue()).toBe(`<p>[]a</p>`, {
                    message: "p3 should not have the same document as p1",
                });

                peers.p1.destroyEditor();

                expect(p2Spies.recoverFromStaleDocument.callCount).toBe(0, {
                    message: "p2 recoverFromStaleDocument should not have been called",
                });
                expect(p2Spies.resetFromServerAndResyncWithPeers.callCount).toBe(0, {
                    message: "p2 resetFromServerAndResyncWithPeers should not have been called",
                });
                expect(p2Spies.processMissingSteps.callCount).toBe(0, {
                    message: "p2 processMissingSteps should not have been called",
                });
                expect(p2Spies.applySnapshot.callCount).toBe(0, {
                    message: "p2 applySnapshot should not have been called",
                });

                await peers.p2.setOnline();
                expect(peers.p2.getValue()).toBe(`[]<p>ab</p>`, {
                    message: "p2 should have the same document as p1",
                });
                expect(peers.p3.getValue()).toBe(`<p>[]a</p>`, {
                    message: "p3 should not have the same document as p1",
                });

                expect(p2Spies.recoverFromStaleDocument.callCount).toBe(1, {
                    message: "p2 recoverFromStaleDocument should have been called once",
                });
                expect(p2Spies.resetFromServerAndResyncWithPeers.callCount).toBe(1, {
                    message: "p2 resetFromServerAndResyncWithPeers should have been called once",
                });
                expect(p2Spies.processMissingSteps.callCount).toBe(0, {
                    message: "p2 processMissingSteps should not have been called",
                });
                expect(p2Spies.applySnapshot.callCount).toBe(0, {
                    message: "p2 applySnapshot should not have been called",
                });

                await peers.p3.setOnline();
                expect(peers.p3.getValue()).toBe(`[]<p>ab</p>`, {
                    message: "p3 should have the same document as p1",
                });
                expect(p3Spies.recoverFromStaleDocument.callCount).toBe(1, {
                    message: "p3 recoverFromStaleDocument should have been called once",
                });
                expect(p3Spies.resetFromServerAndResyncWithPeers.callCount).toBe(0, {
                    message: "p3 resetFromServerAndResyncWithPeers should not have been called",
                });
                expect(p3Spies.processMissingSteps.callCount).toBe(1, {
                    message: "p3 processMissingSteps should have been called once",
                });
                expect(p3Spies.applySnapshot.callCount).toBe(1, {
                    message: "p3 applySnapshot should have been called once",
                });
                expect(p3Spies.onRecoveryPeerTimeout.callCount).toBe(0, {
                    message: "p3 onRecoveryPeerTimeout should not have been called",
                });
            });
            test("should recover from snapshot after PTP_MAX_RECOVERY_TIME if some peer do not respond", async () => {
                const pool = await createPeers(["p1", "p2", "p3"]);
                const peers = pool.peers;

                await peers.p1.focus();
                await peers.p2.focus();
                await peers.p3.focus();

                await peers.p1.openDataChannel(peers.p2);
                await peers.p1.openDataChannel(peers.p3);
                await peers.p2.openDataChannel(peers.p3);
                peers.p2.setOffline();
                peers.p3.setOffline();

                const p2Spies = makeSpies(peers.p2.plugins.collaborationOdoo, [
                    "recoverFromStaleDocument",
                    "resetFromServerAndResyncWithPeers",
                    "processMissingSteps",
                    "applySnapshot",
                ]);
                const p3Spies = makeSpies(peers.p3.plugins.collaborationOdoo, [
                    "recoverFromStaleDocument",
                    "resetFromServerAndResyncWithPeers",
                    "processMissingSteps",
                    "applySnapshot",
                    "onRecoveryPeerTimeout",
                ]);

                await insertEditorText(peers.p1.editor, "b");
                await peers.p1.writeToServer();
                peers.p1.setOffline();

                expect(peers.p1.getValue()).toBe(`<p>ab[]</p>`, {
                    message: "p1 have inserted char b",
                });
                expect(peers.p2.getValue()).toBe(`<p>[]a</p>`, {
                    message: "p2 should not have the same document as p1",
                });
                expect(peers.p3.getValue()).toBe(`<p>[]a</p>`, {
                    message: "p3 should not have the same document as p1",
                });

                expect(p2Spies.recoverFromStaleDocument.callCount).toBe(0, {
                    message: "p2 recoverFromStaleDocument should not have been called",
                });
                expect(p2Spies.resetFromServerAndResyncWithPeers.callCount).toBe(0, {
                    message: "p2 resetFromServerAndResyncWithPeers should not have been called",
                });
                expect(p2Spies.processMissingSteps.callCount).toBe(0, {
                    message: "p2 processMissingSteps should not have been called",
                });
                expect(p2Spies.applySnapshot.callCount).toBe(0, {
                    message: "p2 applySnapshot should not have been called",
                });

                await peers.p2.setOnline();
                expect(peers.p2.getValue()).toBe(`[]<p>ab</p>`, {
                    message: "p2 should have the same document as p1",
                });
                expect(peers.p3.getValue()).toBe(`<p>[]a</p>`, {
                    message: "p3 should not have the same document as p1",
                });

                expect(p2Spies.recoverFromStaleDocument.callCount).toBe(1, {
                    message: "p2 recoverFromStaleDocument should have been called once",
                });
                expect(p2Spies.resetFromServerAndResyncWithPeers.callCount).toBe(1, {
                    message: "p2 resetFromServerAndResyncWithPeers should have been called once",
                });
                expect(p2Spies.processMissingSteps.callCount).toBe(0, {
                    message: "p2 processMissingSteps should not have been called",
                });
                expect(p2Spies.applySnapshot.callCount).toBe(0, {
                    message: "p2 applySnapshot should not have been called",
                });

                await peers.p3.setOnline();
                expect(peers.p3.getValue()).toBe(`[]<p>ab</p>`, {
                    message: "p3 should have the same document as p1",
                });
                expect(p3Spies.recoverFromStaleDocument.callCount).toBe(1, {
                    message: "p3 recoverFromStaleDocument should have been called once",
                });
                expect(p3Spies.resetFromServerAndResyncWithPeers.callCount).toBe(0, {
                    message: "p3 resetFromServerAndResyncWithPeers should have been called once",
                });
                expect(p3Spies.processMissingSteps.callCount).toBe(1, {
                    message: "p3 processMissingSteps should have been called once",
                });
                expect(p3Spies.applySnapshot.callCount).toBe(1, {
                    message: "p3 applySnapshot should have been called once",
                });
                expect(p3Spies.onRecoveryPeerTimeout.callCount).toBe(1, {
                    message: "p3 onRecoveryPeerTimeout should have been called once",
                });
            });
        });
        describe("recover from server", () => {
            test("should recover from server if no snapshot have been processed", async () => {
                const pool = await createPeers(["p1", "p2", "p3"]);
                const peers = pool.peers;

                await peers.p1.focus();
                await peers.p2.focus();
                await peers.p3.focus();

                await peers.p1.openDataChannel(peers.p2);
                await peers.p1.openDataChannel(peers.p3);
                await peers.p2.openDataChannel(peers.p3);
                peers.p2.setOffline();
                peers.p3.setOffline();

                const p2Spies = makeSpies(peers.p2.plugins.collaborationOdoo, [
                    "recoverFromStaleDocument",
                    "resetFromServerAndResyncWithPeers",
                    "processMissingSteps",
                    "applySnapshot",
                    "onRecoveryPeerTimeout",
                    "resetFromPeer",
                ]);

                const p3Spies = makeSpies(peers.p3.plugins.collaborationOdoo, [
                    "recoverFromStaleDocument",
                    "resetFromServerAndResyncWithPeers",
                    "processMissingSteps",
                    "applySnapshot",
                    "onRecoveryPeerTimeout",
                    "resetFromPeer",
                ]);

                await insertEditorText(peers.p1.editor, "b");
                await peers.p1.writeToServer();

                expect(peers.p1.getValue()).toBe(`<p>ab[]</p>`, {
                    message: "p1 have inserted char b",
                });
                expect(peers.p2.getValue()).toBe(`<p>[]a</p>`, {
                    message: "p2 should not have the same document as p1",
                });
                expect(peers.p3.getValue()).toBe(`<p>[]a</p>`, {
                    message: "p3 should not have the same document as p1",
                });

                peers.p1.destroyEditor();

                expect(p2Spies.recoverFromStaleDocument.callCount).toBe(0, {
                    message: "p2 recoverFromStaleDocument should not have been called",
                });
                expect(p2Spies.resetFromServerAndResyncWithPeers.callCount).toBe(0, {
                    message: "p2 resetFromServerAndResyncWithPeers should not have been called",
                });
                expect(p2Spies.processMissingSteps.callCount).toBe(0, {
                    message: "p2 processMissingSteps should not have been called",
                });
                expect(p2Spies.applySnapshot.callCount).toBe(0, {
                    message: "p2 applySnapshot should not have been called",
                });
                expect(p2Spies.onRecoveryPeerTimeout.callCount).toBe(0, {
                    message: "p2 onRecoveryPeerTimeout should not have been called",
                });
                expect(p2Spies.resetFromPeer.callCount).toBe(0, {
                    message: "p2 resetFromPeer should not have been called",
                });

                // Because we do not wait for the end of the
                // p2.setOnline promise, p3 will not be able to reset
                // from p2 wich allow us to test that p3 reset from the
                // server as a fallback.
                peers.p2.setOnline();
                await peers.p3.setOnline();

                expect(peers.p3.getValue()).toBe(`<p>[]ab</p>`, {
                    message: "p3 should have the same document as p1",
                });

                expect(p3Spies.recoverFromStaleDocument.callCount).toBe(1, {
                    message: "p3 recoverFromStaleDocument should have been called once",
                });
                expect(p3Spies.resetFromServerAndResyncWithPeers.callCount).toBe(1, {
                    message: "p3 resetFromServerAndResyncWithPeers should have been called once",
                });
                expect(p3Spies.processMissingSteps.callCount).toBe(0, {
                    message: "p3 processMissingSteps should not have been called",
                });
                expect(p3Spies.applySnapshot.callCount).toBe(1, {
                    message: "p3 applySnapshot should have been called once",
                });
                expect(p3Spies.onRecoveryPeerTimeout.callCount).toBe(0, {
                    message: "p3 onRecoveryPeerTimeout should not have been called",
                });
                expect(p3Spies.resetFromPeer.callCount).toBe(1, {
                    message: "p3 resetFromPeer should have been called once",
                });
            });
            test("should recover from server if there is no peer connected", async () => {
                const pool = await createPeers(["p1", "p2"]);
                const peers = pool.peers;

                await peers.p1.focus();
                await peers.p2.focus();

                await peers.p1.openDataChannel(peers.p2);
                peers.p2.setOffline();

                const p2Spies = makeSpies(peers.p2.plugins.collaborationOdoo, [
                    "recoverFromStaleDocument",
                    "resetFromServerAndResyncWithPeers",
                    "processMissingSteps",
                    "applySnapshot",
                    "onRecoveryPeerTimeout",
                    "resetFromPeer",
                ]);

                await insertEditorText(peers.p1.editor, "b");
                await peers.p1.writeToServer();

                expect(peers.p1.getValue()).toBe(`<p>ab[]</p>`, {
                    message: "p1 have inserted char b",
                });
                expect(peers.p2.getValue()).toBe(`<p>[]a</p>`, {
                    message: "p2 should not have the same document as p1",
                });

                peers.p1.destroyEditor();

                expect(p2Spies.recoverFromStaleDocument.callCount).toBe(0, {
                    message: "p2 recoverFromStaleDocument should not have been called",
                });
                expect(p2Spies.resetFromServerAndResyncWithPeers.callCount).toBe(0, {
                    message: "p2 resetFromServerAndResyncWithPeers should not have been called",
                });
                expect(p2Spies.processMissingSteps.callCount).toBe(0, {
                    message: "p2 processMissingSteps should not have been called",
                });
                expect(p2Spies.applySnapshot.callCount).toBe(0, {
                    message: "p2 applySnapshot should not have been called",
                });
                expect(p2Spies.resetFromPeer.callCount).toBe(0, {
                    message: "p2 resetFromPeer should not have been called",
                });

                await peers.p2.setOnline();
                expect(peers.p2.getValue()).toBe(`[]<p>ab</p>`, {
                    message: "p2 should have the same document as p1",
                });

                expect(p2Spies.recoverFromStaleDocument.callCount).toBe(1, {
                    message: "p2 recoverFromStaleDocument should have been called once",
                });
                expect(p2Spies.resetFromServerAndResyncWithPeers.callCount).toBe(1, {
                    message: "p2 resetFromServerAndResyncWithPeers should have been called once",
                });
                expect(p2Spies.processMissingSteps.callCount).toBe(0, {
                    message: "p2 processMissingSteps should not have been called",
                });
                expect(p2Spies.applySnapshot.callCount).toBe(0, {
                    message: "p2 applySnapshot should not have been called",
                });
                expect(p2Spies.onRecoveryPeerTimeout.callCount).toBe(0, {
                    message: "p2 onRecoveryPeerTimeout should not have been called",
                });
                expect(p2Spies.resetFromPeer.callCount).toBe(0, {
                    message: "p2 resetFromPeer should not have been called",
                });
            });
            test("should recover from server if there is no response after PTP_MAX_RECOVERY_TIME", async () => {
                const pool = await createPeers(["p1", "p2", "p3"]);
                const peers = pool.peers;

                await peers.p1.focus();
                await peers.p2.focus();

                await peers.p1.openDataChannel(peers.p2);
                await peers.p1.openDataChannel(peers.p3);
                await peers.p2.openDataChannel(peers.p3);
                peers.p2.setOffline();
                peers.p3.setOffline();

                const p2Spies = makeSpies(peers.p2.plugins.collaborationOdoo, [
                    "recoverFromStaleDocument",
                    "resetFromServerAndResyncWithPeers",
                    "processMissingSteps",
                    "applySnapshot",
                    "onRecoveryPeerTimeout",
                    "resetFromPeer",
                ]);

                await insertEditorText(peers.p1.editor, "b");
                await peers.p1.writeToServer();
                peers.p1.setOffline();

                expect(peers.p1.getValue()).toBe(`<p>ab[]</p>`, {
                    message: "p1 have inserted char b",
                });
                expect(peers.p2.getValue()).toBe(`<p>[]a</p>`, {
                    message: "p2 should not have the same document as p1",
                });
                expect(peers.p3.getValue()).toBe(`<p>[]a</p>`, {
                    message: "p3 should not have the same document as p1",
                });

                expect(p2Spies.recoverFromStaleDocument.callCount).toBe(0, {
                    message: "p2 recoverFromStaleDocument should not have been called",
                });
                expect(p2Spies.resetFromServerAndResyncWithPeers.callCount).toBe(0, {
                    message: "p2 resetFromServerAndResyncWithPeers should not have been called",
                });
                expect(p2Spies.processMissingSteps.callCount).toBe(0, {
                    message: "p2 processMissingSteps should not have been called",
                });
                expect(p2Spies.applySnapshot.callCount).toBe(0, {
                    message: "p2 applySnapshot should not have been called",
                });
                expect(p2Spies.resetFromPeer.callCount).toBe(0, {
                    message: "p2 resetFromPeer should not have been called",
                });

                await peers.p2.setOnline();
                expect(peers.p2.getValue()).toBe(`[]<p>ab</p>`, {
                    message: "p2 should have the same document as p1",
                });
                expect(peers.p3.getValue()).toBe(`<p>[]a</p>`, {
                    message: "p3 should not have the same document as p1",
                });

                expect(p2Spies.recoverFromStaleDocument.callCount).toBe(1, {
                    message: "p2 recoverFromStaleDocument should have been called once",
                });
                expect(p2Spies.resetFromServerAndResyncWithPeers.callCount).toBe(1, {
                    message: "p2 resetFromServerAndResyncWithPeers should have been called once",
                });
                expect(p2Spies.processMissingSteps.callCount).toBe(0, {
                    message: "p2 processMissingSteps should not have been called",
                });
                expect(p2Spies.applySnapshot.callCount).toBe(0, {
                    message: "p2 applySnapshot should not have been called",
                });
                expect(p2Spies.onRecoveryPeerTimeout.callCount).toBe(1, {
                    message: "p2 onRecoveryPeerTimeout should have been called once",
                });
                // p1 and p3 are considered offline but not
                // disconnected. It means that p2 will try to recover
                // from p1 and p3 even if they are currently
                // unavailable. This test is usefull to check that the
                // code path to resetFromPeer is properly taken.
                expect(p2Spies.resetFromPeer.callCount).toBe(2, {
                    message: "p2 resetFromPeer should have been called twice",
                });
            });
        });
    });
});
describe("Disconnect & reconnect", () => {
    test("should sync history when disconnecting and reconnecting to internet", async () => {
        const pool = await createPeers(["p1", "p2"]);
        const peers = pool.peers;

        await peers.p1.focus();
        await peers.p2.focus();
        await peers.p1.openDataChannel(peers.p2);

        await insertEditorText(peers.p1.editor, "b");

        peers.p1.setOffline();

        const setSelection = (peer) => {
            const selection = peer.document.getSelection();
            const pElement = peer.editor.editable.querySelector("p");
            const range = new Range();
            range.setStart(pElement.firstChild, 1);
            range.setEnd(pElement.firstChild, 1);
            selection.removeAllRanges();
            selection.addRange(range);
        };
        const addP = (peer, content) => {
            const p = document.createElement("p");
            p.textContent = content;
            peer.editor.editable.append(p);
            peer.editor.shared.history.addStep();
        };

        setSelection(peers.p1);
        await insertEditorText(peers.p1.editor, "c");

        addP(peers.p1, "d");

        setSelection(peers.p2);
        await insertEditorText(peers.p2.editor, "e");
        addP(peers.p2, "f");

        peers.p1.setOnline();
        peers.p2.setOnline();

        // todo: p1PromiseForMissingStep and p2PromiseForMissingStep
        // should be removed when the fix of undetected missing step
        // will be merged. (task-3208277)
        const p1PromiseForMissingStep = new Promise((resolve) => {
            patch(peers.p2.plugins.collaborationOdoo, {
                async processMissingSteps() {
                    // Wait for the p2PromiseForMissingStep to resolve
                    // to avoid undetected missing step.
                    await p2PromiseForMissingStep;
                    super.processMissingSteps(...arguments);
                    resolve();
                },
            });
        });
        const p2PromiseForMissingStep = new Promise((resolve) => {
            patch(peers.p1.plugins.collaborationOdoo, {
                async processMissingSteps() {
                    super.processMissingSteps(...arguments);
                    resolve();
                },
            });
        });

        await peers.p1.openDataChannel(peers.p2);
        await p1PromiseForMissingStep;

        expect(peers.p1.getValue()).toBe(`<p>ac[]b</p><p>f</p><p>d</p>`, {
            message: "p1 should have the value merged with p2",
        });
        expect(peers.p2.getValue()).toBe(`<p>ac[]b</p><p>f</p><p>d</p>`, {
            message: "p2 should have the value merged with p1",
        });
    });
});

describe("Snapshot", () => {
    test("should destroy snapshot interval when the editor is destroyed", async () => {
        const pool = await createPeers(["p1"]);
        const peers = pool.peers;
        const editor = peers.p1.editor;
        await peers.p1.focus();
        await insertEditorText(peers.p1.editor, "b");
        editor.destroy();
        await advanceTime(2 * HISTORY_SNAPSHOT_INTERVAL);
        expect(peers.p1.plugins.collaboration._snapshotInterval).toBe(false);
    });
    test("should get the steps from the first made snapshot of a reseted peer", async () => {
        const pool = await createPeers(["p1", "p2", "p3"]);
        const peers = pool.peers;

        await peers.p1.focus();
        await peers.p2.focus();
        await peers.p3.focus();

        await peers.p1.openDataChannel(peers.p2);

        await insertEditorText(peers.p1.editor, "b");
        await animationFrame();

        await advanceTime(HISTORY_SNAPSHOT_INTERVAL);

        await peers.p2.openDataChannel(peers.p3);

        expect(peers.p3.getValue()).toBe(`<p>[]ab</p>`, {
            message: "p3 should have the steps from the first snapshot of p2",
        });
    });
});

describe("History steps Ids", () => {
    test("should clear history step ids from the DOM at start up", async () => {
        const pool = await createPeers(["p1"]);
        const peers = pool.peers;
        const editor = peers.p1.editor;
        await peers.p1.focus();
        expect(getContent(editor.editable)).toBe("<p>a[]</p>");
        editor.destroy();
    });

    test("should clear history step ids when resetting from server", async () => {
        const pool = await createPeers(["p1", "p2"]);
        const peers = pool.peers;

        await peers.p1.focus();
        await insertEditorText(peers.p1.editor, "b");
        await peers.p1.writeToServer();

        expect(peers.p2.plugins.collaborationOdoo.isDocumentStale).toBe(true, {
            message: "p2 should have a stale document",
        });

        await peers.p2.focus();
        await peers.p1.openDataChannel(peers.p2);
        // This timeout is necessary for the selection to be set
        await new Promise((resolve) => setTimeout(resolve));

        expect(peers.p2.plugins.collaborationOdoo.isDocumentStale).toBe(false, {
            message: "p2 should not have a stale document",
        });
        expect(getContent(peers.p2.editor.editable)).toBe(`<p>[]ab</p>`, {
            message:
                "p2 should have the same document as p1, without the history steps id attribute",
        });
    });

    test("should not add history step ids to a split block's children", async () => {
        const pool = await createPeers(["p1"]);
        const peers = pool.peers;
        const editor = peers.p1.editor;
        await peers.p1.focus();
        editor.shared.split.splitBlock();
        editor.shared.history.addStep();
        expect(getContent(editor.editable)).toBe(
            `<p>a</p><p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>`
        );
        editor.shared.split.splitBlock();
        editor.shared.history.addStep();
        expect(getContent(editor.editable)).toBe(
            `<p>a</p><p><br></p><p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>`
        );
        editor.destroy();
    });
});

describe("Selection", () => {
    test("Selection should be updated for peer after delete backward", async () => {
        const pool = await createPeers(["p1", "p2"]);
        // editor content : <p>a</p>
        const peers = pool.peers;
        await peers.p1.focus(); // <p>a[]</p>
        await peers.p2.focus();
        await peers.p1.openDataChannel(peers.p2);
        await animationFrame();
        await new Promise((resolve) => setTimeout(resolve));
        expect(
            peers.p2.plugins.collaborationSelectionAvatar.selectionInfos.get("p1").selection
                .anchorOffset
        ).toBe(1);
        expect(
            peers.p2.plugins.collaborationSelection.selectionInfos.get("p1").selection.anchorOffset
        ).toBe(1);
        peers.p1.plugins.delete.delete("backward", "character");
        await waitUntil(() => {
            const selectionInAvatarPlugin =
                peers.p2.plugins.collaborationSelectionAvatar.selectionInfos.get("p1").selection.anchorOffset == 0;
            const selectionInCollabSelectionPlugin =
                peers.p2.plugins.collaborationSelection.selectionInfos.get("p1").selection.anchorOffset == 0;
            return selectionInAvatarPlugin && selectionInCollabSelectionPlugin;
        });
        expect(
            peers.p2.plugins.collaborationSelectionAvatar.selectionInfos.get("p1").selection
                .anchorOffset
        ).toBe(0);
        expect(
            peers.p2.plugins.collaborationSelection.selectionInfos.get("p1").selection.anchorOffset
        ).toBe(0);
    });
});
