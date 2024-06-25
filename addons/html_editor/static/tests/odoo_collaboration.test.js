/** @odoo-module */

import { stripHistoryIds } from "@html_editor/others/collaboration/collaboration_odoo_plugin";
import { HISTORY_SNAPSHOT_INTERVAL } from "@html_editor/others/collaboration/collaboration_plugin";
import { COLLABORATION_PLUGINS, MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { Wysiwyg } from "@html_editor/wysiwyg";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { Mutex } from "@web/core/utils/concurrency";
import { patch } from "@web/core/utils/patch";
import { getContent, getSelection, setSelection } from "./_helpers/selection";
import { insertText } from "./_helpers/user_actions";
import { animationFrame, advanceTime } from "@odoo/hoot-mock";
import { RemoteConnections } from "@html_editor/others/collaboration/remote/RemoteConnections";

/**
 * @typedef PeerPool
 * @property {Record<string, PeerTest>} peers
 * @property {string} lastRecordSaved
 *
 * @typedef {import("@html_editor/others/collaboration/collaboration_odoo_plugin").CollaborationOdooPlugin} CollaborationOdooPlugin
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
    /**
     * @type {RemoteConnections}
     */
    remoteConnections = null;

    constructor() {
        this.connections = new Set();
        this.onlineMutex = new Mutex();
        this.isOnline = true;
    }
    /**
     * @param {Object} infos
     * @param {string} infos.peerId
     * @param {import("@html_editor/plugin").Editor} infos.editor
     * @param {Object} infos.plugins
     * @param {CollaborationOdooPlugin} infos.plugins.collaboration_odoo
     * @param {PeerPool} infos.pool
     * @param {PeerPool['peers']} peers
     * @param {Document} document
     *
     */
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
        this.plugins.collaboration_odoo.ptpJoined = true;
    }
    /**
     * @param {PeerTest} fromPeer
     */
    async ping(fromPeer) {
        this.connections.add(fromPeer);
        fromPeer.connections.add(this);

        fromPeer.remoteConnections.notifyPeer(
            this.peerId,
            "remote_ping",
            fromPeer.remoteConnections.config.getRemotePingPayload()
        );
    }
    getValue() {
        return stripHistoryIds(getContent(this.editor.editable));
    }
    async writeToServer() {
        this.pool.lastRecordSaved = this.editor.getContent();
        const lastId = this.plugins.collaboration_odoo.getLastHistoryStepId(
            this.pool.lastRecordSaved
        );
        for (const peer of Object.values(this.peers)) {
            if (peer === this) {
                continue;
            }
            peer.onlineMutex.exec(async () => {
                return peer.plugins.collaboration_odoo.onServerLastIdUpdate(String(lastId));
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
            const plugins = Object.fromEntries(editor.plugins.map((p) => [p.constructor.name, p]));
            /** @type {PeerPool}*/
            const { pool } = this.props;
            const { peers } = pool;

            patch(plugins["collaboration_odoo"], {
                getMetadata() {
                    const result = super.getMetadata();
                    result.avatarUrl = ``;
                    return result;
                },
                async setupCollaboration(...args) {
                    super.setupCollaboration(...args);
                    this.startCollaborationTime = parseInt(peerId.match(/\d+/));
                    this.remoteLoading = this.remoteLoading.then(() => {
                        loadedResolver();
                        peers[peerId].remoteConnections = this.remoteConnections;
                    });
                },
                getRemoteConnections(config) {
                    const odooPlugin = this;
                    class PatchedRemoteConnections extends RemoteConnections {
                        async start() {
                            this.remoteInterface = {
                                stop() {
                                    odooPlugin.remoteConnections.notifyAllPeers("remove_peer");
                                },
                                notifyAllPeers() {
                                    for (const peer of peers[peerId].connections) {
                                        this.notifyPeer(peer.peerId, ...arguments);
                                    }
                                },
                                notifyPeer(toPeerId, notificationName, notificationPayload) {
                                    if (
                                        notificationName !== "remove_peer" &&
                                        (!peers[toPeerId].isOnline || !peers[peerId].isOnline)
                                    ) {
                                        return;
                                    }
                                    peers[toPeerId].remoteConnections.handleNotification(
                                        notificationName,
                                        peerId,
                                        structuredClone(notificationPayload)
                                    );
                                },
                            };
                        }
                    }
                    return new PatchedRemoteConnections(config);
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

function insertEditorText(editor, text) {
    insertText(editor, text);
    editor.dispatch("ADD_STEP");
}

beforeEach(() => {
    onRpc("/web/dataset/call_kw/res.users/read", () => {
        return [{ id: 0, name: "admin" }];
    });
    onRpc("/html_editor/get_collab_infos", () => {
        return { ice_servers: [] };
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

        insertEditorText(peers.p1.editor, "b");

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

        await peers.p1.ping(peers.p2);
        insertEditorText(peers.p1.editor, "b");
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

        insertEditorText(peers.p1.editor, "b");

        await peers.p1.ping(peers.p2);
        await new Promise((resolve) => setTimeout(resolve));

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
            await peers.p1.ping(peers.p2);
            await new Promise((resolve) => setTimeout(resolve));

            insertEditorText(peers.p1.editor, "b");
            await new Promise((resolve) => setTimeout(resolve));

            await peers.p1.writeToServer();

            expect(peers.p1.plugins.collaboration_odoo.isDocumentStale).toBe(false, {
                message: "p1 should not have a stale document",
            });
            expect(peers.p1.getValue()).toBe(`<p>ab[]</p>`, {
                message: "p1 should have the same document as p2",
            });

            expect(peers.p2.plugins.collaboration_odoo.isDocumentStale).toBe(false, {
                message: "p2 should not have a stale document",
            });
            expect(peers.p2.getValue()).toBe(`<p>[]ab</p>`, {
                message: "p2 should have the same document as p1",
            });

            expect(peers.p3.plugins.collaboration_odoo.isDocumentStale).toBe(true, {
                message: "p3 should have a stale document",
            });
            expect(peers.p3.getValue()).toBe(`<p>a[]</p>`, {
                message: "p3 should not have the same document as p1",
            });

            await peers.p3.focus();
            await peers.p1.ping(peers.p3);
            await new Promise((resolve) => setTimeout(resolve));

            expect(peers.p3.plugins.collaboration_odoo.isDocumentStale).toBe(false, {
                message: "p3 should not have a stale document",
            });
            expect(peers.p3.getValue()).toBe(`<p>[]ab</p>`, {
                message: "p3 should have the same document as p1",
            });

            insertEditorText(peers.p1.editor, "c");

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
                await peers.p1.ping(peers.p2);
                await peers.p1.ping(peers.p3);
                await peers.p2.ping(peers.p3);
                await new Promise((resolve) => setTimeout(resolve));

                const p3Spies = makeSpies(peers.p3.plugins.collaboration_odoo, [
                    "recoverFromStaleDocument",
                    "resetFromServerAndResyncWithPeers",
                    "addMissingSteps",
                    "applySnapshot",
                ]);

                expect(peers.p1.plugins.collaboration_odoo.historyShareId).toBe(
                    peers.p2.plugins.collaboration_odoo.historyShareId,
                    {
                        message: "p1 and p2 should have the same historyShareId",
                    }
                );
                expect(peers.p1.plugins.collaboration_odoo.historyShareId).toBe(
                    peers.p3.plugins.collaboration_odoo.historyShareId,
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

                insertEditorText(peers.p1.editor, "b");

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
                expect(peers.p1.plugins.collaboration_odoo.isDocumentStale).toBe(false, {
                    message: "p1 should not have a stale document",
                });
                expect(peers.p2.plugins.collaboration_odoo.isDocumentStale).toBe(false, {
                    message: "p2 should not have a stale document",
                });
                expect(peers.p3.plugins.collaboration_odoo.isDocumentStale).toBe(false, {
                    message: "p3 should not have a stale document",
                });

                await peers.p3.setOnline();

                expect(p3Spies.recoverFromStaleDocument.callCount).toBe(1, {
                    message: "p3 recoverFromStaleDocument should have been called once",
                });
                expect(p3Spies.addMissingSteps.callCount).toBe(1, {
                    message: "p3 addMissingSteps should have been called once",
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

                await peers.p1.ping(peers.p2);
                await peers.p1.ping(peers.p3);
                await peers.p2.ping(peers.p3);
                await new Promise((resolve) => setTimeout(resolve));
                peers.p2.setOffline();
                peers.p3.setOffline();

                const p2Spies = makeSpies(peers.p2.plugins.collaboration_odoo, [
                    "recoverFromStaleDocument",
                    "resetFromServerAndResyncWithPeers",
                    "addMissingSteps",
                    "applySnapshot",
                ]);
                const p3Spies = makeSpies(peers.p3.plugins.collaboration_odoo, [
                    "recoverFromStaleDocument",
                    "resetFromServerAndResyncWithPeers",
                    "addMissingSteps",
                    "applySnapshot",
                    "onRecoveryPeerTimeout",
                ]);

                insertEditorText(peers.p1.editor, "b");

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
                await new Promise((resolve) => setTimeout(resolve));

                expect(p2Spies.recoverFromStaleDocument.callCount).toBe(0, {
                    message: "p2 recoverFromStaleDocument should not have been called",
                });
                expect(p2Spies.resetFromServerAndResyncWithPeers.callCount).toBe(0, {
                    message: "p2 resetFromServerAndResyncWithPeers should not have been called",
                });
                expect(p2Spies.addMissingSteps.callCount).toBe(0, {
                    message: "p2 addMissingSteps should not have been called",
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
                expect(p2Spies.addMissingSteps.callCount).toBe(0, {
                    message: "p2 addMissingSteps should not have been called",
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
                expect(p3Spies.addMissingSteps.callCount).toBe(0, {
                    message: "p3 addMissingSteps should not have been called",
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

                await peers.p1.ping(peers.p2);
                await peers.p1.ping(peers.p3);
                await peers.p2.ping(peers.p3);
                await new Promise((resolve) => setTimeout(resolve));
                peers.p2.setOffline();
                peers.p3.setOffline();

                const p2Spies = makeSpies(peers.p2.plugins.collaboration_odoo, [
                    "recoverFromStaleDocument",
                    "resetFromServerAndResyncWithPeers",
                    "addMissingSteps",
                    "applySnapshot",
                ]);
                const p3Spies = makeSpies(peers.p3.plugins.collaboration_odoo, [
                    "recoverFromStaleDocument",
                    "resetFromServerAndResyncWithPeers",
                    "addMissingSteps",
                    "applySnapshot",
                    "onRecoveryPeerTimeout",
                ]);

                insertEditorText(peers.p1.editor, "b");
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
                expect(p2Spies.addMissingSteps.callCount).toBe(0, {
                    message: "p2 addMissingSteps should not have been called",
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
                expect(p2Spies.addMissingSteps.callCount).toBe(0, {
                    message: "p2 addMissingSteps should not have been called",
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
                expect(p3Spies.addMissingSteps.callCount).toBe(0, {
                    message: "p3 addMissingSteps should not have been called",
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

                await peers.p1.ping(peers.p2);
                await peers.p1.ping(peers.p3);
                await peers.p2.ping(peers.p3);
                await new Promise((resolve) => setTimeout(resolve));
                peers.p2.setOffline();
                peers.p3.setOffline();

                const p2Spies = makeSpies(peers.p2.plugins.collaboration_odoo, [
                    "recoverFromStaleDocument",
                    "resetFromServerAndResyncWithPeers",
                    "processMissingSteps",
                    "applySnapshot",
                    "onRecoveryPeerTimeout",
                    "resetFromPeer",
                ]);

                const p3Spies = makeSpies(peers.p3.plugins.collaboration_odoo, [
                    "recoverFromStaleDocument",
                    "resetFromServerAndResyncWithPeers",
                    "processMissingSteps",
                    "applySnapshot",
                    "onRecoveryPeerTimeout",
                    "resetFromPeer",
                ]);

                insertEditorText(peers.p1.editor, "b");
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

                await peers.p1.ping(peers.p2);
                await new Promise((resolve) => setTimeout(resolve));
                peers.p2.setOffline();

                const p2Spies = makeSpies(peers.p2.plugins.collaboration_odoo, [
                    "recoverFromStaleDocument",
                    "resetFromServerAndResyncWithPeers",
                    "processMissingSteps",
                    "applySnapshot",
                    "onRecoveryPeerTimeout",
                    "resetFromPeer",
                ]);

                insertEditorText(peers.p1.editor, "b");
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

                await peers.p1.ping(peers.p2);
                await peers.p1.ping(peers.p3);
                await peers.p2.ping(peers.p3);
                await new Promise((resolve) => setTimeout(resolve));
                peers.p2.setOffline();
                peers.p3.setOffline();

                const p2Spies = makeSpies(peers.p2.plugins.collaboration_odoo, [
                    "recoverFromStaleDocument",
                    "resetFromServerAndResyncWithPeers",
                    "processMissingSteps",
                    "applySnapshot",
                    "onRecoveryPeerTimeout",
                    "resetFromPeer",
                ]);

                insertEditorText(peers.p1.editor, "b");
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
        await peers.p1.ping(peers.p2);
        await new Promise((resolve) => setTimeout(resolve));

        insertEditorText(peers.p1.editor, "b");

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
            peer.editor.dispatch("ADD_STEP");
        };

        setSelection(peers.p1);
        insertEditorText(peers.p1.editor, "c");
        addP(peers.p1, "d");

        setSelection(peers.p2);
        insertEditorText(peers.p2.editor, "e");
        addP(peers.p2, "f");

        peers.p1.setOnline();
        peers.p2.setOnline();

        await peers.p1.ping(peers.p2);
        await new Promise((resolve) => setTimeout(resolve));

        expect(peers.p1.getValue()).toBe(`<p>ac[]b</p><p>f</p><p>d</p>`, {
            message: "p1 should have the value merged with p2",
        });
        expect(peers.p2.getValue()).toBe(`<p>ac[]b</p><p>f</p><p>d</p>`, {
            message: "p2 should have the value merged with p1",
        });
    });
});

describe("Destroy odoo collaboration plugin", () => {
    test("should destroy snapshot interval", async () => {
        const pool = await createPeers(["p1"]);
        const peers = pool.peers;
        const editor = peers.p1.editor;
        await peers.p1.focus();
        insertEditorText(peers.p1.editor, "b");
        editor.destroy();
        await advanceTime(2 * HISTORY_SNAPSHOT_INTERVAL);
        expect(peers.p1.plugins.collaboration._snapshotInterval).toBe(false);
    });
});
