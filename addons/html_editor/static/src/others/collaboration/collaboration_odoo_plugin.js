import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { debounce } from "@web/core/utils/timing";
import { RemoteConnectionError, RemoteConnections } from "./remote/RemoteConnections";
import { Mutex } from "@web/core/utils/concurrency";
import { RequestError } from "./remote/remoteHelpers";

/**
 * @typedef {Object} CollaborationSelection
 * @property {import("@html_editor/core/history_plugin").SerializedSelection} selection
 * @property {string} color
 * @property {string} peerId
 */

// Time to consider a user offline in ms. This fixes the problem of the
// navigator closing rtc connection when the mac laptop screen is closed.
// const CONSIDER_OFFLINE_TIME = 1000;
// Check wether the computer could be offline. This fixes the problem of the
// navigator closing rtc connection when the mac laptop screen is closed.
// This case happens on Mac OS on every browser when the user close it's laptop
// screen. At first, the os/navigator closes all rtc connection, and after some
// times, the os/navigator internet goes offline without triggering an
// offline/online event.
// However, if the laptop screen is open and the connection is properly remove
// (e.g. disconnect wifi), the event is properly triggered.
// const CHECK_OFFLINE_TIME = 1000;
// const PTP_PEER_DISCONNECTED_STATES = ["failed", "closed", "disconnected"];

// Time in ms to wait when trying to aggregate snapshots from other peers and
// potentially recover from a missing step before trying to apply those
// snapshots or recover from the server.
const PTP_MAX_RECOVERY_TIME = 500;

const REQUEST_ERROR = Symbol("REQUEST_ERROR");

// this is a local cache for ice server descriptions
let ICE_SERVERS = null;

export class CollaborationOdooPlugin extends Plugin {
    static name = "collaboration_odoo";
    static dependencies = ["history", "collaboration", "selection"];
    static shared = ["getPeerMetadata"];
    /** @type { (p: CollaborationOdooPlugin) => Record<string, any> } */
    static resources = (p) => ({
        onSelectionChange: debounce(() => {
            p.remoteConnections?.notifyAllPeers(
                "oe_history_set_selection",
                p.getCurrentCollaborativeSelection()
            );
        }, 50),
        onExternalMissingParentStep: p.onExternalMissingParentStep.bind(p),
    });

    setup() {
        this.isDocumentStale = false;
        this.ptpJoined = false;
        this.peerMetadatas = {};

        // Each time a reset of the document is triggered, it is assigned a
        // unique identifier. Since resetting the editor involves asynchronous
        // requests, it is possible that subsequent resets are triggered before
        // the previous one is complete. This property identifies the latest
        // reset and can be compared against to cancel the processing of late
        // responses from previous resets.
        this.lastCollaborationResetId = 0;

        // The ID is the latest step ID that the server knows through
        // `data-last-history-steps`. We cannot save to the server if we do not
        // have that ID in our history ids as it means that our version is
        // stale.
        this.serverLastStepId =
            this.config.content && this.getLastHistoryStepId(this.config.content);

        this.setupCollaboration(this.config.collaboration.collaborationChannel);

        const collaborativeTrigger = this.config.collaboration.collaborativeTrigger;
        this.joinPeerToPeer = this.joinPeerToPeer.bind(this);
        if (collaborativeTrigger === "start" || typeof collaborativeTrigger === "undefined") {
            this.joinPeerToPeer();
        } else if (collaborativeTrigger === "focus") {
            // Wait until editor is focused to join the peer to peer network.
            this.editable.addEventListener("focus", this.joinPeerToPeer);
        }
    }
    destroy() {
        this.collaborationStopBus?.();
        // If peer to peer is initializing, wait for properly closing it.
        if (this.remoteLoading) {
            this.remoteLoading.then(() => {
                this.stopRemote();
            });
        }
        // todo: to implement
        // clearInterval(this.collaborationInterval);
        super.destroy();
    }

    handleCommand(commandName, payload) {
        switch (commandName) {
            case "STEP_ADDED":
                this.remoteConnections?.notifyAllPeers?.("oe_history_step", payload.step);
                break;
            case "CLEAN":
                // TODO @phoenix: evaluate if this should be cleanforsave instead
                this.attachHistoryIds(payload.root);
                break;
            case "HISTORY_RESET":
                this.onReset(payload.content);
                break;
        }
    }

    stopRemote() {
        this.joiningPtp = false;
        this.ptpJoined = false;
        this.resetCollabRequests();
        this.remoteConnections.stop();
    }

    getCurrentCollaborativeSelection() {
        const selection = this.shared.getEditableSelection();
        return {
            selection: this.shared.serializeSelection(selection),
            peerId: this.config.collaboration.peerId,
        };
    }
    setupCollaboration(collaborationChannel) {
        const modelName = collaborationChannel.collaborationModelName;
        const fieldName = collaborationChannel.collaborationFieldName;
        const resId = collaborationChannel.collaborationResId;
        const channelName = `editor_collaboration:${modelName}:${fieldName}:${resId}`;

        if (!(modelName && fieldName && resId)) {
            return;
        }

        this.collaborationChannelName = channelName;

        this.listenCollaborationBus(modelName, fieldName, resId);
        this.startCollaborationTime = new Date().getTime();

        // todo: handle this feature
        // this.checkConnectionChange = () => {
        //     if (!this.ptp) {
        //         return;
        //     }
        //     if (!navigator.onLine) {
        //         this.signalOffline();
        //     } else {
        //         this.signalOnline();
        //     }
        // };

        // window.addEventListener("online", this.checkConnectionChange);
        // window.addEventListener("offline", this.checkConnectionChange);

        // this.collaborationInterval = setInterval(async () => {
        //     if (this.offlineTimeout || this.preSavePromise || !this.ptp) {
        //         return;
        //     }

        //     const peersInfos = Object.values(this.ptp.peersInfos);
        //     const couldBeDisconnected =
        //         Boolean(peersInfos.length) &&
        //         peersInfos.every((x) =>
        //             PTP_PEER_DISCONNECTED_STATES.includes(
        //                 x.peerConnection && x.peerConnection.connectionState
        //             )
        //         );

        //     if (couldBeDisconnected) {
        //         this.offlineTimeout = setTimeout(() => {
        //             this.signalOffline();
        //         }, CONSIDER_OFFLINE_TIME);
        //     }
        // }, CHECK_OFFLINE_TIME);

        const loadCollabInfos = async () => {
            const infos = await rpc("/html_editor/get_collab_infos", {
                model_name: modelName,
                field_name: fieldName,
                res_id: resId,
                peer_id: this.config.collaboration.peerId,
            });
            ICE_SERVERS = infos.ice_servers;

            let iceServers = ICE_SERVERS;
            if (!iceServers.length) {
                iceServers = [
                    {
                        urls: ["stun:stun1.l.google.com:19302", "stun:stun2.l.google.com:19302"],
                    },
                ];
            }
            this.iceServers = iceServers;
            this.sfuConfig = infos.sfu_config;
        };

        this.remoteLoading = loadCollabInfos().then(() => {
            const handlers = getRemoteHandlers(this);
            const config = {
                peerId: this.config.collaboration.peerId,
                RemoteConnections,
                handleNotification: (notificationName, fromPeerId, notificationPayload) => {
                    for (const dict of this.resources.handleCollaborationNotification || []) {
                        dict[notificationName]?.(fromPeerId, notificationPayload);
                    }
                    handlers.notificationHandlers?.[notificationName]?.(
                        fromPeerId,
                        notificationPayload
                    );
                },
                handleRequest: (requestName, fromPeerId, notificationPayload) => {
                    return handlers.requestHandlers?.[requestName]?.(
                        fromPeerId,
                        notificationPayload.requestPayload
                    );
                },
                getRemotePingPayload: () => ({
                    metadata: this.getMetadata(),
                    historyShareId: this.historyShareId,
                }),
            };
            if (this.sfuConfig) {
                this.remoteType = "sfu";
                config.sfuConfig = this.sfuConfig;
            } else {
                this.remoteType = "peerToPeer";
                const rpcMutex = new Mutex();
                config.peerToPeerConfig = {
                    iceServers: this.iceServers,
                    broadcastAll: (rpcData) => {
                        return rpcMutex.exec(async () => {
                            return rpc("/html_editor/bus_broadcast", {
                                model_name: modelName,
                                field_name: fieldName,
                                res_id: resId,
                                bus_data: rpcData,
                            });
                        });
                    },
                };
            }
            this.remoteConnections = this.getRemoteConnections(config);
            this.remoteConnections.start().catch((e) => {
                if (e instanceof RemoteConnectionError) {
                    this.services.notification.add(e.message, {
                        type: "warning",
                    });
                } else {
                    throw e;
                }
            });
        });
    }
    getRemoteConnections(config) {
        return new RemoteConnections(config);
    }
    listenCollaborationBus(modelName, fieldName, resId) {
        const collaborationBusListener = async (payload) => {
            if (
                payload.model_name === modelName &&
                payload.field_name === fieldName &&
                payload.res_id === resId
            ) {
                if (payload.notificationName === "html_field_write") {
                    this.onServerLastIdUpdate(payload.notificationPayload.last_step_id);
                } else if (this.remoteType === "peerToPeer" && this.ptpJoined) {
                    await this.remoteLoading;
                    this.remoteConnections.remoteInterface.handleExternalNotification(payload);
                }
            }
        };
        const { busService } = this.config.collaboration;
        busService.subscribe("editor_collaboration", collaborationBusListener);
        busService.addChannel(this.collaborationChannelName);
        this.collaborationStopBus = () => {
            busService.unsubscribe("editor_collaboration", collaborationBusListener);
            busService.deleteChannel(this.collaborationChannelName);
        };
    }

    /**
     * @param {string} peerId
     */
    getPeerMetadata(peerId) {
        return this.peerMetadatas[peerId];
    }
    /**
     * @param {CollaborationSelection} selection
     */
    onExternalMultiselectionUpdate(selection) {
        this.resources.collaborativeSelectionUpdate?.forEach((cb) => cb(selection));
    }

    async requestPeer(peerId, requestName, requestPayload) {
        return (
            this.remoteConnections &&
            this.remoteConnections.requestPeer(peerId, requestName, requestPayload).catch((e) => {
                if (e instanceof RequestError) {
                    return REQUEST_ERROR;
                } else {
                    throw e;
                }
            })
        );
    }
    getMetadata() {
        const metadatas = {
            startTime: this.startCollaborationTime,
            peerName: user.name,
        };
        for (const cb of this.resources.getCollaborationPeerMetadata || []) {
            Object.assign(metadatas, cb());
        }
        return metadatas;
    }
    /**
     * Update the server document last step id and recover from a stale document
     * if this peer does not have that step in its history.
     */
    onServerLastIdUpdate(last_step_id) {
        this.serverLastStepId = last_step_id;
        // Check if the current document is stale.
        this.isDocumentStale = this.isLastDocumentStale();
        // todo: Add test that it works for SFU and peer to peer.
        if (this.isDocumentStale && (this.sfuConfig || this.ptpJoined)) {
            return this.recoverFromStaleDocument();
        } else if (this.isDocumentStale && this.joiningPtp) {
            // In case there is a stale document while a previous recovery is
            // ongoing.
            this.resetCollabRequests();
            this.joinPeerToPeer();
        }
    }

    async joinPeerToPeer() {
        await this.remoteLoading;
        if (!this.remoteConnections) {
            return;
        }
        // Only try to join if there is no SFU server (to connect in peer to peer).
        if (this.sfuConfig) {
            return;
        }
        this.editable.removeEventListener("focus", this.joinPeerToPeer);
        this.joiningPtp = true;
        if (this.isDocumentStale) {
            const success = await this.resetFromServerAndResyncWithPeers();
            if (!success) {
                return;
            }
        }
        this.remoteConnections.remoteInterface.ptpJoin();
        this.joiningPtp = false;
        this.ptpJoined = true;
    }
    isLastDocumentStale() {
        if (!this.serverLastStepId) {
            return false;
        }
        return !this.shared.getBranchIds().includes(this.serverLastStepId);
    }

    /**
     * Try to recover from a stale document.
     *
     * The strategy is:
     *
     * 1.  Try to get a converging document from the other peers.
     *
     * 1.1 By recovery from missing steps: it is the best possible case of
     *     retrieval.
     *
     * 1.2 By recovery from snapshot: it reset the whole editor (destroying
     *     changes and selection made by the user).
     *
     * 2. Reset from the server:
     *    If the recovery from the other peers fails, reset from the server.
     *
     *    As we know we have a stale document, we need to reset it at least from
     *    the server. We shouldn't wait too long for peers to respond because
     *    the longer we wait for an unresponding peer, the longer a user can
     *    edit a stale document.
     *
     *    The peers timeout is set to PTP_MAX_RECOVERY_TIME.
     */
    async recoverFromStaleDocument() {
        return new Promise((resolve) => {
            // 1. Try to recover a converging document from other peers.
            const resetCollabCount = this.lastCollaborationResetId;

            const allPeers = this.getPeers().map((peer) => peer.id);

            if (allPeers.length === 0) {
                if (this.isDocumentStale) {
                    this.showConflictDialog();
                    resolve();
                    return this.resetFromServerAndResyncWithPeers();
                }
            }

            let hasRetrievalBudgetTimeout = false;
            const snapshots = [];
            let nbPendingResponses = allPeers.length;

            const success = () => {
                resolve();
                clearTimeout(timeout);
            };

            for (const peerId of allPeers) {
                this.requestPeer(peerId, "recover_document", {
                    serverDocumentId: this.serverLastStepId,
                    fromStepId: this.shared.getBranchIds().at(-1),
                }).then((response) => {
                    nbPendingResponses--;
                    if (
                        response === REQUEST_ERROR ||
                        resetCollabCount !== this.lastCollaborationResetId ||
                        hasRetrievalBudgetTimeout ||
                        !response ||
                        !this.isDocumentStale
                    ) {
                        if (nbPendingResponses <= 0) {
                            processSnapshots();
                        }
                        return;
                    }
                    if (response.missingSteps && response.missingSteps.length) {
                        // todo: what if the steps will be on the externalStepsBuffers?
                        this.addMissingSteps(response.missingSteps, peerId);
                        this.isDocumentStale = this.isLastDocumentStale();
                    }
                    snapshots.push(response.snapshot);
                    if (nbPendingResponses < 1) {
                        processSnapshots();
                    }
                });
            }

            // Only process the snapshots after having received a response from all
            // the peers or after PTP_MAX_RECOVERY_TIME in order to try to recover
            // from missing steps.
            const processSnapshots = async () => {
                this.isDocumentStale = this.isLastDocumentStale();
                if (!this.isDocumentStale) {
                    return success();
                }
                if (snapshots[0]) {
                    this.showConflictDialog();
                }
                for (const snapshot of snapshots) {
                    this.applySnapshot(snapshot);
                    this.isDocumentStale = this.isLastDocumentStale();
                    // Prevent reseting from another snapshot if the document
                    // converge.
                    if (!this.isDocumentStale) {
                        return success();
                    }
                }

                // 2. If the document is still stale, try to recover from the server.
                if (this.isDocumentStale) {
                    this.showConflictDialog();
                    await this.resetFromServerAndResyncWithPeers();
                }

                success();
            };

            // Wait PTP_MAX_RECOVERY_TIME to retrieve data from other peers to
            // avoid reseting from the server if possible.
            const timeout = setTimeout(() => {
                if (resetCollabCount !== this.lastCollaborationResetId) {
                    return;
                }
                hasRetrievalBudgetTimeout = true;
                this.onRecoveryPeerTimeout(processSnapshots);
            }, PTP_MAX_RECOVERY_TIME);
        });
    }

    /**
     * Get peers.
     */
    getPeers() {
        const peers = Object.entries(this.peerMetadatas).map(([peerId, metadata]) => ({
            id: peerId,
            startTime: metadata.startTime,
        }));
        return peers.sort((a, b) => (isPeerFirst(a, b) ? -1 : 1));
    }

    getLastHistoryStepId(value) {
        const matchId = value.match(/data-last-history-steps="(?:[0-9]+,)*([0-9]+)"/);
        return matchId && matchId[1];
    }

    resetCollabRequests() {
        this.lastCollaborationResetId++;
        // By aborting the current requests from ptp, we ensure that the ongoing
        // `Wysiwyg.requestPeer` will return REQUEST_ERROR. Most requests that
        // calls `Wysiwyg.requestPeer` might want to check if the response is
        // REQUEST_ERROR.
        this.remoteConnections.abortCurrentRequests();
    }
    /**
     * Reset the document from the server and resync with the peers.
     */
    async resetFromServerAndResyncWithPeers() {
        let collaborationResetId = this.lastCollaborationResetId;
        const record = await this.getCurrentRecord();
        if (collaborationResetId !== this.lastCollaborationResetId) {
            return false;
        }

        let content = record[this.config.collaboration.collaborationChannel.collaborationFieldName];
        const lastHistoryId = content && this.getLastHistoryStepId(content);
        // If a change was made in the document while retrieving it, the
        // lastHistoryId will be different if the odoo bus did not have time to
        // notify the user.
        if (this.serverLastStepId !== lastHistoryId) {
            // todo: instrument it to ensure it never happens
            throw new Error(
                "Concurency detected while recovering from a stale document. The last history id of the server is different from the history id received by the html_field_write event."
            );
        }

        this.isDocumentStale = false;
        content = content || "<p><br></p>";
        // content here is trusted
        this.editable.innerHTML = content;
        this.dispatch("NORMALIZE", { node: this.editable });
        this.shared.reset(content);

        // After resetting from the server, try to resynchronise with a peer as
        // if it was the first time connecting to a peer in order to retrieve a
        // proper snapshot (e.g. This case could arise if we tried to recover
        // from a peer but the timeout (PTP_MAX_RECOVERY_TIME) was reached
        // before receiving a response).
        this.resetCollabRequests();
        collaborationResetId = this.lastCollaborationResetId;
        this.startCollaborationTime = new Date().getTime();
        await Promise.all(
            this.getPeers().map((peer) => {
                // Reset from the fastest peer. The first peer to reset will set
                // resets.
                return this.resetFromPeer(peer.id, collaborationResetId);
            })
        );
        this.isStaleDocument = this.isLastDocumentStale();
        if (this.isStaleDocument) {
            return false;
        }
        return true;
    }
    onReset(content) {
        // This ID correspond to the peer that initiated the document and set
        // the initial oid for all nodes in the tree. It is not the same as
        // document that had a step id at some point. If a step comes from a
        // different history, we should not apply it.
        this.historyShareId = Math.floor(Math.random() * Math.pow(2, 52)).toString();

        const lastStepId = content && this.getLastHistoryStepId(content);
        if (lastStepId) {
            this.shared.setInitialBranchStepId(lastStepId);
        }
    }

    addMissingSteps(missingSteps, originPeerId) {
        this.shared.onExternalHistorySteps(missingSteps, originPeerId);
    }
    applySnapshot(snapshot) {
        const { steps, historyIds, historyShareId } = snapshot;
        // If there is no serverLastStepId, it means that we use a document
        // that is not versionned yet.
        const isStaleDocument =
            this.serverLastStepId && !historyIds.includes(this.serverLastStepId);
        if (isStaleDocument) {
            return;
        }
        this.historyShareId = historyShareId;
        this.shared.resetFromSteps(steps, historyIds);

        // todo: ensure that if the selection was not in the editable before the
        // reset, it remains where it was after applying the snapshot.
        return true;
    }

    /**
     * Callback for when the timeout PTP_MAX_RECOVERY_TIME fires.
     *
     * Used to be hooked in tests.
     *
     * @param {Function} processSnapshots The snapshot processing function.
     */
    async onRecoveryPeerTimeout(processSnapshots) {
        processSnapshots();
    }
    showConflictDialog() {
        // todo: implement conflict dialog
        // if (this.conflictDialogOpened) {
        //     return;
        // }
        // const content = markup(this.odooEditor.editable.cloneNode(true).outerHTML);
        // this.conflictDialogOpened = true;
        // this.env.services.dialog.add(ConflictDialog, {
        //     content,
        //     close: () => (this.conflictDialogOpened = false),
        // });
    }

    getHistorySnapshot() {
        const snapshot = this.shared.getSnapshotSteps();
        return Object.assign({}, snapshot, {
            steps: snapshot.steps,
            historyShareId: this.historyShareId,
        });
    }

    async resetFromPeer(fromPeerId, resetCollabCount) {
        const snapshot = await this.requestPeer(fromPeerId, "get_history_from_snapshot", undefined);
        if (snapshot === REQUEST_ERROR) {
            return REQUEST_ERROR;
        }
        if (resetCollabCount !== this.lastCollaborationResetId) {
            return;
        }
        // Ensure that the history hasn't been synced by another peer before
        // this `get_history_from_snapshot` finished.
        if (this.lastResetPeerCount && this.lastResetPeerCount >= this.lastCollaborationResetId) {
            return;
        }
        const applied = this.applySnapshot(snapshot);
        if (!applied) {
            return;
        }
        this.isDocumentStale = this.isLastDocumentStale();

        this.lastResetPeerCount = this.lastCollaborationResetId;
        this.shared.setCursorStart(this.editable.firstChild);
        this.remoteConnections.notifyAllPeers("oe_get_selection");
        // Ask the steps in case some other steps were not received meanwhile.
        this.remoteConnections.notifyAllPeers("oe_get_last_step");
        this.editable.dispatchEvent(new CustomEvent("onHistoryResetFromPeer"));
    }

    async onExternalMissingParentStep({ step, fromStepId, originPeerId }) {
        const missingSteps = await this.requestPeer(originPeerId, "get_missing_steps", {
            fromStepId: fromStepId,
            toStepId: step.id,
        });
        if (missingSteps === REQUEST_ERROR) {
            return;
        }

        // If missing steps === -1, it means:
        // 1) stale document: the step.peerId has a stale document
        // 2) snapshot: the step.peerId has a snapshot and does not includes the step in
        //   its history
        // 3) if another share history id
        //   - because the step.peerId has reset from the server and
        //     step.peerId is not synced with this peer
        //   - because the step.peerId is in a network partition
        if (missingSteps === -1) {
            // todo: in case 2 (snapshot), we should try first to apply all the
            // steps in the history of that peer instead of reseting.
            // todo:
            // - what if there is 3 peer connecting at the same time and
            //   peer2 reset from peer1 while peer3 reset from peer2?
            // - what if peer2 reset from peer1 while peer1 reset from peer2?
            this.resetCollabRequests();
            this.resetFromPeer(originPeerId, this.lastCollaborationResetId);
            return;
        } else if (!missingSteps.length) {
            return;
        }
        this.addMissingSteps(missingSteps.concat(step), originPeerId);
    }
    async getCurrentRecord() {
        const [record] = await this.config.collaboration.ormService.read(
            this.config.collaboration.collaborationChannel.collaborationModelName,
            [this.config.collaboration.collaborationChannel.collaborationResId],
            [this.config.collaboration.collaborationChannel.collaborationFieldName]
        );
        return record;
    }
    attachHistoryIds(editable) {
        // Clean existing 'data-last-history-steps' attributes.
        editable
            .querySelectorAll("[data-last-history-steps]")
            .forEach((el) => el.removeAttribute("data-last-history-steps"));

        const historyIds = this.shared.getBranchIds().join(",");
        const firstChild = editable.children[0];
        if (firstChild) {
            firstChild.setAttribute("data-last-history-steps", historyIds);
        }
    }
}

/**
 * @param {CollaborationOdooPlugin} plugin
 */
function getRemoteHandlers(plugin) {
    return {
        notificationHandlers: {
            // This signal is send from a peer that just joined the network or
            // when a peer is disconnected and reconnected.
            remote_ping: (fromPeerId, { metadata, historyShareId }) => {
                plugin.peerMetadatas[fromPeerId] = metadata;
                plugin.remoteConnections.notifyPeer(fromPeerId, "remote_pong", {
                    metadata: plugin.getMetadata(),
                    selection: plugin.getCurrentCollaborativeSelection(),
                    lastHistoryStep: plugin.shared.getHistorySteps().at(-1),
                    historyShareId: plugin.historyShareId,
                });
                if (historyShareId === plugin.historyShareId) {
                    plugin.remoteConnections.notifyPeer(fromPeerId, "oe_get_last_step");
                    plugin.remoteConnections.notifyPeer(fromPeerId, "oe_get_selection");
                }
            },
            remote_pong: async (
                fromPeerId,
                { metadata, selection, lastHistoryStep, historyShareId }
            ) => {
                plugin.peerMetadatas[fromPeerId] = metadata;

                if (historyShareId !== plugin.historyShareId) {
                    plugin.resetCollabRequests();
                    plugin.resetFromPeer(fromPeerId, plugin.lastCollaborationResetId);
                    return;
                }
                // todo: what if other steps arrive in the meantime?
                plugin.onExternalMultiselectionUpdate(selection);
                plugin.shared.onExternalHistorySteps([lastHistoryStep], fromPeerId);
            },
            oe_history_step: (fromPeerId, notificationPayload) => {
                plugin.shared.onExternalHistorySteps([notificationPayload], fromPeerId);
            },
            oe_get_selection: (fromPeerId) => {
                plugin.remoteConnections.notifyPeer(
                    fromPeerId,
                    "oe_history_set_selection",
                    plugin.getCurrentCollaborativeSelection()
                );
            },
            oe_history_set_selection: (fromPeerId, notificationPayload) => {
                if (!plugin.peerMetadatas[fromPeerId]) {
                    return;
                }
                const selection = notificationPayload;
                plugin.onExternalMultiselectionUpdate(selection);
            },
            oe_get_last_step: (fromPeerId) => {
                plugin.remoteConnections.notifyPeer(
                    fromPeerId,
                    "oe_history_step",
                    plugin.shared.getHistorySteps().at(-1)
                );
            },
            // todo: Ensure the peer is always removed in SFU and Peer to peer
            remove_peer: (fromPeerId) => {
                delete plugin.peerMetadatas[fromPeerId];
            },
        },
        requestHandlers: {
            get_missing_steps: (fromPeerId, requestPayload) =>
                plugin.shared.historyGetMissingSteps(requestPayload),
            get_history_from_snapshot: () => plugin.getHistorySnapshot(),
            get_collaborative_selection: () => plugin.getCurrentCollaborativeSelection(),
            recover_document: (fromPeerId, { serverDocumentId, fromStepId }) => {
                if (!plugin.shared.getBranchIds().includes(serverDocumentId)) {
                    return;
                }
                return {
                    missingSteps: plugin.shared.historyGetMissingSteps({ fromStepId }),
                    snapshot: plugin.getHistorySnapshot(),
                };
            },
        },
    };
}

/**
 * Check wether peerA is before peerB.
 */
function isPeerFirst(peerA, peerB) {
    if (peerA.startTime === peerB.startTime) {
        return peerA.id.localeCompare(peerB.id) === -1;
    }
    if (peerA.startTime === undefined || peerB.startTime === undefined) {
        return Boolean(peerA.startTime);
    } else {
        return peerA.startTime < peerB.startTime;
    }
}

/**
 * @param {string} value
 */
export function stripHistoryIds(value) {
    return (value && value.replace(/\sdata-last-history-steps="[^"]*?"/, "")) || value;
}
