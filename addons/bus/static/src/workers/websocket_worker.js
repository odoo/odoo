/** @odoo-module native */
import { debounce, Deferred, Logger } from "./bus_worker_utils.js";
import {
    CONNECTION_STATE,
    WEBSOCKET_CLOSE_CODES,
    WEBSOCKET_READY_STATE,
} from "./websocket_worker_constants.js";

/**
 * Type of events that can be sent from the worker to its clients.
 *
 * @typedef { 'BUS:CONNECT' | 'BUS:RECONNECT' | 'BUS:DISCONNECT' | 'BUS:RECONNECTING' | 'BUS:NOTIFICATION' | 'BUS:INITIALIZED' | 'BUS:OUTDATED'| 'BUS:WORKER_STATE_UPDATED' | 'BUS:PROVIDE_LOGS' | 'BUS:PING' } WorkerEvent
 */

/**
 * Type of action that can be sent from the client to the worker.
 *
 * @typedef {'BUS:ADD_CHANNEL' | 'BUS:DELETE_CHANNEL' | 'BUS:SET_CHANNELS' | 'BUS:FORCE_UPDATE_CHANNELS' | 'BUS:INITIALIZE_CONNECTION' | 'BUS:REQUEST_LOGS' | 'BUS:SEND' | 'BUS:SET_LOGGING_ENABLED' | 'BUS:LEAVE' | 'BUS:STOP' | 'BUS:START' | 'BUS:PONG'} WorkerAction
 */

const MAXIMUM_RECONNECT_DELAY = 60000;
const UUID = Date.now().toString(36) + Math.random().toString(36).substring(2);
const logger = new Logger("bus_websocket_worker");

// Client actions that (re)establish an evicted/departed client's participation
// in the bus, and so may re-register it in `channelsByClient`. An allowlist
// (not "any BUS:* except LEAVE/PONG"): actions that do NOT express intent to
// receive notifications — BUS:STOP, BUS:SEND, BUS:DELETE_CHANNEL,
// BUS:REQUEST_LOGS, BUS:SET_LOGGING_ENABLED, BUS:FORCE_UPDATE_CHANNELS — must
// never resurrect a client that called stop() or was evicted, otherwise a
// stopped tab silently starts receiving broadcasts again (an unguarded
// `offline`→BUS:STOP was exactly such a resurrection).
const REREGISTERING_ACTIONS = new Set([
    "BUS:INITIALIZE_CONNECTION",
    "BUS:START",
    "BUS:ADD_CHANNEL",
    "BUS:SET_CHANNELS",
]);

/**
 * Per-connection state for one WebSocket lifetime.
 *
 * Bundling it here — rather than as loose worker fields (`websocket`,
 * `firstSubscribeDeferred`, `lastChannelSubscription`) reset at four different
 * sites — makes the invariant "no state from a previous connection leaks into
 * the next one" structural instead of comment-enforced:
 *
 * - a new connection is a new ``Connection``, so its subscribe gate
 *   (``subscribeDeferred``) and subscription cache (``lastSubscription``) start
 *   fresh automatically — no open-time/close-time/stop-time resets needed;
 * - a superseded connection is identified by ``epoch``, so a late event from a
 *   replaced socket is ignored instead of acting on the current connection.
 */
class Connection {
    constructor(socket, epoch) {
        this.socket = socket;
        this.epoch = epoch;
        // Resolves once THIS connection has sent its own `subscribe`; queued
        // messages flush only after it, so they never race ahead of the
        // subscription. A fresh connection ⇒ a fresh (unresolved) gate.
        this.subscribeDeferred = new Deferred();
        // Last `subscribe` payload sent on THIS connection (dedup). Null ⇒ the
        // next `_updateChannels` (re)subscribes — exactly the "always subscribe
        // on a fresh connection" invariant, obtained for free.
        this.lastSubscription = null;
    }
}

/**
 * This class regroups the logic necessary in order for the
 * SharedWorker/Worker to work. Indeed, Safari and some minor browsers
 * do not support SharedWorker. In order to solve this issue, a Worker
 * is used in this case. The logic is almost the same than the one used
 * for SharedWorker and this class implements it.
 */
export class WebsocketWorker {
    INITIAL_RECONNECT_DELAY = 1000;
    /**
     * Ceiling on the random spread added to a reconnect delay. The spread
     * applied is `min(connectRetryDelay, RECONNECT_JITTER)`, so it widens with
     * the attempt instead of being a flat window -- see
     * `_retryConnectionWithDelay`.
     */
    RECONNECT_JITTER = 30_000;
    CONNECTION_CHECK_DELAY = 60_000;
    // How often dead clients are looked for, and how long a client may stay
    // silent before it is pinged (half the timeout) then evicted (full
    // timeout). Deliberately generous: a bfcache-frozen tab cannot answer
    // pings, and while `bus_service` replays its channels on `pageshow`, an
    // aggressive timeout would churn subscriptions for nothing.
    CLIENT_LIVENESS_SWEEP_DELAY = 120_000;
    CLIENT_LIVENESS_TIMEOUT = 600_000;
    // How long a dispatched notification id is remembered for deduplication.
    // Mirrors the server's hold-back window (`Websocket.
    // MAX_NOTIFICATION_HISTORY_SEC = 10` in bus/websocket.py): the server
    // deliberately re-delivers ids it cannot yet prove were received exactly
    // once, and holds `last_id` back for that many seconds so notifications
    // committed out of id order by concurrent transactions are not skipped.
    // Anything older than the window can no longer be legitimately re-sent,
    // so remembering it here would be pure memory overhead. Kept a bit larger
    // than the server's to absorb clock/scheduling slack.
    SEEN_NOTIFICATION_RETENTION_MS = 15_000;
    // Defensive cap: a pathological notification flood must not grow the
    // seen-id map without bound between prunes.
    SEEN_NOTIFICATION_MAX_COUNT = 10_000;
    // Pacing for the reconnect flush of `messageWaitQueue`.
    //
    // The server rate-limits INCOMING frames (`Websocket._limit_rate`:
    // `websocket_rate_limit_burst` frames, default 10, per
    // `burst * websocket_rate_limit_delay` seconds, default 2s) and answers a
    // breach by closing with TRY_LATER. Flushing the queue in one tight loop
    // therefore killed the connection outright as soon as 10 messages had
    // piled up while offline -- measured exactly: 9 queued messages survive,
    // 10 close the freshly opened socket. Two uncoordinated subsystems, one
    // constant apart from a reconnect loop.
    //
    // 4 frames per second stays under the server's *sustainable* rate
    // (1/delay = 5/s) rather than merely under its burst, so the limiter's
    // sliding window never fills no matter how long the queue is.
    FLUSH_CHUNK_SIZE = 4;
    FLUSH_CHUNK_DELAY = 1000;
    // Nothing bounded the offline queue. Presence/keepalive-style messages are
    // worthless by the time a long outage ends, so keep the most recent ones
    // and drop the stale head rather than growing without limit.
    MESSAGE_QUEUE_MAX = 200;

    constructor(name) {
        this.name = name;
        // Timestamp of start of most recent bus service sender
        this.newestStartTs = undefined;
        this.websocketURL = "";
        this.currentUID = null;
        this.currentDB = null;
        this.isWaitingForNewUID = true;
        this.channelsByClient = new Map();
        // Last time each client was heard from — feeds the liveness sweep: a
        // tab that crashed or was OOM-killed never sends BUS:LEAVE, and its
        // port would otherwise stay in `channelsByClient` forever, keeping
        // the server subscribed to channels no live tab wants and receiving
        // every broadcast.
        this.lastSeenByClient = new Map();
        this._startClientLivenessSweep();
        this.connectRetryDelay = this.INITIAL_RECONNECT_DELAY;
        this.connectTimeout = null;
        this.debugModeByClient = new Map();
        this.isDebug = false;
        this.active = true;
        this.state = CONNECTION_STATE.IDLE;
        this.isReconnecting = false;
        this.loggingEnabled = null;
        // Current WebSocket connection (socket + its subscribe gate and
        // subscription cache), or null when no socket is live. See `Connection`.
        this._connection = null;
        // Monotonic id stamped on each connection, so a superseded socket's late
        // events can be told apart from the current one's.
        this._epoch = 0;
        // Highest notification id seen so far. NOT used for deduplication
        // (see `seenNotificationIds`): only sent as `last` on subscribe.
        this.lastNotificationId = 0;
        // Recently dispatched notification ids (id -> seen timestamp), kept
        // for `SEEN_NOTIFICATION_RETENTION_MS`. This is the dedup source of
        // truth: the server may legitimately deliver LOWER ids in LATER
        // batches (its hold-back window for out-of-order commits), so a
        // monotonic watermark filter would silently drop them.
        this.seenNotificationIds = new Map();
        this.messageWaitQueue = [];
        // Handle of the paced flush in progress, so `_stop` can cancel it.
        this._flushTimeout = null;
        // Sticky for the whole debounce window: a forced request must not be
        // downgraded by a plain one arriving after it. Consumed when the
        // updater fires.
        this._forceNextUpdate = false;
        // ONE debounced updater for both the plain and the forced path. Two
        // independent debouncers could each fire in the same window and send
        // two identical subscribes, because `force` bypasses the dedup guard in
        // `_updateChannels`. Discuss does exactly that on every thread pin:
        // `addChannel` arms the plain path while mail's store patch calls
        // `forceUpdateChannels`.
        this._debouncedUpdateChannels = debounce(() => {
            const force = this._forceNextUpdate;
            this._forceNextUpdate = false;
            this._updateChannels({ force });
        }, 300);
        this._debouncedSendToServer = debounce(this._sendToServer, 300);

        this._onWebsocketClose = this._onWebsocketClose.bind(this);
        this._onWebsocketError = this._onWebsocketError.bind(this);
        this._onWebsocketMessage = this._onWebsocketMessage.bind(this);
        this._onWebsocketOpen = this._onWebsocketOpen.bind(this);

        globalThis.addEventListener("error", ({ error }) => {
            const params =
                error instanceof Error
                    ? [error.constructor.name, error.stack]
                    : [error];
            this._logDebug("Unhandled error", ...params);
        });
        globalThis.addEventListener("unhandledrejection", ({ reason }) => {
            const params =
                reason instanceof Error
                    ? [reason.constructor.name, reason.stack]
                    : [reason];
            this._logDebug("Unhandled rejection", params);
        });
    }

    /**
     * The current connection's socket, or null when none is live. Kept as an
     * accessor so the many `this.websocket` read sites are unchanged while the
     * socket's lifetime is owned by `this._connection`.
     *
     * @returns {WebSocket|null}
     */
    get websocket() {
        return this._connection?.socket ?? null;
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Send the message to all the clients that are connected to the
     * worker.
     *
     * @param {WorkerEvent} type Event to broadcast to connected
     * clients.
     * @param {Object} data
     */
    broadcast(type, data) {
        this._logDebug("broadcast", type, data);
        // No JSON round-trip needed: everything broadcast here is already
        // plain, structured-cloneable data — notification batches come
        // straight out of `JSON.parse` in `_onWebsocketMessage`, the rest are
        // literals built in this file — and `postMessage` structured-clones
        // per client anyway, so the receiving pages never share state with
        // the worker (or with each other).
        for (const client of this.channelsByClient.keys()) {
            client.postMessage({ type, data: data ?? undefined });
        }
    }

    /**
     * Register a client handled by this worker.
     *
     * @param {MessagePort} messagePort
     */
    registerClient(messagePort) {
        messagePort.addEventListener("message", (ev) => {
            this._onClientMessage(messagePort, ev.data);
        });
        this.channelsByClient.set(messagePort, new Map());
        this.lastSeenByClient.set(messagePort, Date.now());
    }

    /**
     * Send message to the given client.
     *
     * @param {MessagePort} client
     * @param {WorkerEvent} type
     * @param {Object} data
     */
    sendToClient(client, type, data) {
        if (type !== "BUS:PROVIDE_LOGS") {
            this._logDebug("sendToClient", type, data);
        }
        // Same provenance guarantee as `broadcast`: data is either parsed
        // JSON or literals built here, and `postMessage` structured-clones —
        // a defensive JSON round-trip would be pure overhead.
        client.postMessage({ type, data: data ?? undefined });
    }

    //--------------------------------------------------------------------------
    // PRIVATE
    //--------------------------------------------------------------------------

    /**
     * Called when a message is posted to the worker by a client (i.e. a
     * MessagePort connected to this worker).
     *
     * @param {MessagePort} client
     * @param {Object} message
     * @param {WorkerAction} [message.action]
     * Action to execute.
     * @param {Object|undefined} [message.data] Data required by the
     * action.
     */
    _onClientMessage(client, { action, data }) {
        this._logDebug("_onClientMessage", action, data);
        if (!this.channelsByClient.has(client) && REREGISTERING_ACTIONS.has(action)) {
            // This client is not (or no longer) registered but is issuing an
            // action that re-establishes bus participation. Two cases produce
            // an unregistered-but-live client: it called stop()/pagehide
            // (BUS:LEAVE) or the liveness sweep evicted it while its tab was
            // frozen. Re-register it with an empty channel map, otherwise a
            // subsequent BUS:ADD_CHANNEL would operate on a missing map.
            this.channelsByClient.set(client, new Map());
            if (action === "BUS:START" || action === "BUS:ADD_CHANNEL") {
                // The client believes it is still subscribed (its page-side
                // channel map survived) but our copy is gone. INITIALIZE and
                // SET_CHANNELS already carry full state; START/ADD_CHANNEL do
                // not, so ask the client to replay its full snapshot. This is
                // the recovery path for a tab evicted while frozen by Page
                // Lifecycle freeze or system suspend, which resume via
                // `resume`/`visibilitychange` — never `pageshow` — so
                // bus_service does not otherwise replay.
                this.sendToClient(client, "BUS:RESYNC");
            }
        }
        // Refresh liveness only for a registered client (possibly just
        // re-registered above). Any message from a live registered port proves
        // it unfrozen; but a message from a departed client (BUS:LEAVE or
        // sweep-evicted) that is not re-registering must not recreate a ghost
        // lastSeen entry — the sweep would then ping it every cycle forever
        // (worker_service auto-pongs, refreshing it), a leak the eviction can
        // never reclaim.
        if (this.channelsByClient.has(client)) {
            this.lastSeenByClient.set(client, Date.now());
        }
        switch (action) {
            case "BUS:SEND": {
                if (data["event_name"] === "update_presence") {
                    this._debouncedSendToServer(data);
                } else {
                    this._sendToServer(data);
                }
                return;
            }
            case "BUS:START":
                return this._start();
            case "BUS:STOP":
                return this._stop();
            case "BUS:LEAVE":
                return this._unregisterClient(client);
            case "BUS:ADD_CHANNEL":
                return this._addChannel(client, data);
            case "BUS:DELETE_CHANNEL":
                return this._deleteChannel(client, data);
            case "BUS:SET_CHANNELS":
                return this._setChannels(client, data);
            case "BUS:FORCE_UPDATE_CHANNELS":
                return this._forceUpdateChannels();
            case "BUS:SET_LOGGING_ENABLED":
                this.loggingEnabled = data;
                break;
            case "BUS:REQUEST_LOGS":
                logger
                    .getLogs()
                    // IndexedDB can be unavailable (private browsing, quota):
                    // still answer with the worker info instead of leaving an
                    // unhandled rejection and a download that never arrives.
                    .catch((error) => [`getLogs failed: ${error}`])
                    .then((logs) => {
                        const workerInfo = {
                            UUID,
                            active: this.active,
                            channels: this._getAllChannels(),
                            db: this.currentDB,
                            is_reconnecting: this.isReconnecting,
                            last_subscription:
                                this._connection?.lastSubscription ?? null,
                            name: this.name,
                            number_of_clients: this.channelsByClient.size,
                            reconnect_delay: this.connectRetryDelay,
                            uid: this.currentUID,
                            websocket_url: this.websocketURL,
                        };
                        this.sendToClient(client, "BUS:PROVIDE_LOGS", {
                            workerInfo,
                            logs,
                        });
                    });
                break;
            case "BUS:INITIALIZE_CONNECTION":
                return this._initializeConnection(client, data);
        }
    }

    /**
     * Add a channel for the given client. Channels are REFCOUNTED per
     * client: several independent features of one tab may claim the same
     * channel (e.g. two im_livechat features), and each of their deletes
     * must only release its own claim. If this channel is not yet known,
     * update the subscription on the server.
     *
     * @param {MessagePort} client
     * @param {string} channel
     */
    _addChannel(client, channel) {
        const clientChannels = this.channelsByClient.get(client);
        clientChannels.set(channel, (clientChannels.get(channel) ?? 0) + 1);
        this._debouncedUpdateChannels();
    }

    /**
     * Release one claim on a channel for the given client; the channel is
     * only removed when its refcount reaches 0. If this channel is not
     * used anymore, update the subscription on the server.
     *
     * @param {MessagePort} client
     * @param {string} channel
     */
    _deleteChannel(client, channel) {
        const clientChannels = this.channelsByClient.get(client);
        const count = clientChannels?.get(channel);
        if (!count) {
            return;
        }
        if (count === 1) {
            clientChannels.delete(channel);
        } else {
            clientChannels.set(channel, count - 1);
        }
        this._debouncedUpdateChannels();
    }

    /**
     * Atomically replace the given client's channel claims. Used by
     * `bus_service` to replay a tab's full channel map (bfcache restore
     * after a liveness eviction, `start()` after `stop()`): a snapshot is
     * immune to the drift an incremental add/delete replay could introduce.
     *
     * @param {MessagePort} client
     * @param {[string, number][]} entries channel -> refcount pairs
     */
    _setChannels(client, entries) {
        const clientChannels = new Map();
        for (const [channel, count] of entries ?? []) {
            if (count > 0) {
                clientChannels.set(channel, count);
            }
        }
        this.channelsByClient.set(client, clientChannels);
        this._debouncedUpdateChannels();
    }

    /**
     * Channels claimed (refcount > 0) by at least one client, sorted.
     *
     * @returns {string[]}
     */
    _getAllChannels() {
        const channels = new Set();
        for (const clientChannels of this.channelsByClient.values()) {
            for (const channel of clientChannels.keys()) {
                channels.add(channel);
            }
        }
        return [...channels].sort();
    }

    /**
     * Update the channels on the server side even if the channels on
     * the client side are the same than the last time we subscribed.
     *
     * Shares the single debounced updater with the plain path: it only raises
     * the sticky flag, so an add and a forced update in the same window
     * collapse into one forced subscribe instead of two.
     */
    _forceUpdateChannels() {
        this._forceNextUpdate = true;
        this._debouncedUpdateChannels();
    }

    /**
     * Remove the given client from this worker client list as well as
     * its channels. If some of its channels are not used anymore,
     * update the subscription on the server.
     *
     * @param {MessagePort} client
     */
    _unregisterClient(client) {
        this.channelsByClient.delete(client);
        this.lastSeenByClient.delete(client);
        this.debugModeByClient.delete(client);
        this.isDebug = [...this.debugModeByClient.values()].some(Boolean);
        this._debouncedUpdateChannels();
    }

    /**
     * Periodically look for dead clients. A tab that crashed or was
     * OOM-killed never sends BUS:LEAVE; without a sweep its port stays
     * registered forever — its channels pad every server subscription and
     * every broadcast posts to a dead port.
     */
    _startClientLivenessSweep() {
        this._lastLivenessSweepTs = Date.now();
        setInterval(
            () => this._sweepClientLiveness(),
            this.CLIENT_LIVENESS_SWEEP_DELAY,
        );
    }

    _sweepClientLiveness() {
        const now = Date.now();
        const sinceLastSweep = now - this._lastLivenessSweepTs;
        this._lastLivenessSweepTs = now;
        if (sinceLastSweep > this.CLIENT_LIVENESS_SWEEP_DELAY * 2) {
            // A whole sweep interval was skipped: timers do not fire while the
            // machine is asleep (or the worker's event loop was blocked), so
            // this is lost time, not genuine client silence. Even a moderate
            // few-minute laptop sleep — well under CLIENT_LIVENESS_TIMEOUT —
            // inflates every client's age by the lost interval, and no tab
            // could answer a BUS:PING during it. Evicting on that age would
            // silently drop live tabs that never got their ping grace (a tab
            // at age > TIMEOUT/2 before the gap jumps straight past TIMEOUT).
            // Grant a fresh window instead — real dead tabs are caught on the
            // next normal sweep.
            for (const client of this.lastSeenByClient.keys()) {
                this.lastSeenByClient.set(client, now);
            }
            return;
        }
        for (const [client, lastSeen] of this.lastSeenByClient) {
            const age = now - lastSeen;
            if (age > this.CLIENT_LIVENESS_TIMEOUT) {
                this._logDebug("liveness_evict", { age });
                this._unregisterClient(client);
            } else if (age > this.CLIENT_LIVENESS_TIMEOUT / 2) {
                // Silent for a while: ask for a sign of life. Live tabs
                // answer BUS:PONG immediately; frozen (bfcache) or dead ones
                // cannot and reach the eviction branch on a later sweep.
                this.sendToClient(client, "BUS:PING");
            }
        }
    }

    /**
     * Initialize a client connection to this worker.
     *
     * @param {Object} param0
     * @param {string} [param0.db] Database name.
     * @param {String} [param0.debug] Current debugging mode for the
     * given client.
     * @param {Number} [param0.lastNotificationId] Last notification id
     * known by the client.
     * @param {String} [param0.websocketURL] URL of the websocket endpoint.
     * @param {Number|false|undefined} [param0.uid] Current user id
     *     - Number: user is logged whether on the frontend/backend.
     *     - false: user is not logged.
     *     - undefined: not available (e.g. livechat support page)
     * @param {Number} param0.startTs Timestamp of start of bus service sender.
     */
    _initializeConnection(
        client,
        { db, debug, lastNotificationId, uid, websocketURL, startTs },
    ) {
        if (this.newestStartTs && this.newestStartTs > startTs) {
            this.debugModeByClient.set(client, debug);
            this.isDebug = [...this.debugModeByClient.values()].some(Boolean);
            this._finishClientInitialization(client);
            return;
        }
        this.newestStartTs = startTs;
        this.websocketURL = websocketURL;
        // Never let a newly-attaching tab rewind the shared high-watermark:
        // its localStorage snapshot may lag behind notifications this worker
        // has already dispatched, which would make the server re-deliver them.
        this.lastNotificationId = Math.max(
            this.lastNotificationId ?? 0,
            lastNotificationId ?? 0,
        );
        this.debugModeByClient.set(client, debug);
        this.isDebug = [...this.debugModeByClient.values()].some(Boolean);
        const isCurrentUserKnown = uid !== undefined;
        if (this.isWaitingForNewUID && isCurrentUserKnown) {
            this.isWaitingForNewUID = false;
            this.currentUID = uid;
        }
        this.currentDB ||= db;
        if (
            (this.currentUID !== uid && isCurrentUserKnown) ||
            (db && this.currentDB !== db)
        ) {
            this.currentUID = uid;
            this.currentDB = db || this.currentDB;
            if (this.websocket) {
                this.websocket.close(WEBSOCKET_CLOSE_CODES.CLEAN);
            }
            this.channelsByClient.forEach((_, key) =>
                this.channelsByClient.set(key, new Map()),
            );
            // The other already-registered clients kept their page-side channel
            // claims but just had their worker-side maps wiped, and (unlike the
            // eviction path) they receive no re-init. Without a RESYNC their
            // channels would be dropped from the next subscribe and never
            // restored (a later incremental ADD_CHANNEL only re-registers the
            // one channel it carries), silently killing bus delivery for those
            // tabs. Ask every client to replay its full channel snapshot; each
            // SET_CHANNELS re-subscribes with the aggregate, so this converges
            // even against the post-switch reconnect.
            this.broadcast("BUS:RESYNC");
            // `bus_bus.id` is a per-database sequence, so the high-watermark
            // and the seen-id history from the previous DB are meaningless
            // (and likely higher / colliding) for the new one. Keeping them
            // would make the subscribe `last` bogus and the dedup filter drop
            // legitimate notifications whose ids happen to collide with
            // recently seen ids of the old DB. Adopt the incoming tab's
            // watermark instead: it is read from the *new* DB's (db-scoped)
            // localStorage key, so it is the correct baseline — resetting to 0
            // would instead subscribe with `last: 0` ("from now") and silently
            // skip notifications committed between that snapshot and the
            // resubscribe. Clear the seen-id history (old-DB ids) and drop
            // now-stale queued messages referencing the old DB's channels.
            this.lastNotificationId = lastNotificationId ?? 0;
            this.seenNotificationIds.clear();
            this.messageWaitQueue = [];
        }
        this._finishClientInitialization(client);
    }

    /**
     * Send the initialization acknowledgements every client must receive,
     * regardless of which `_initializeConnection` path handled it: the worker
     * state, the INITIALIZED handshake, and — when the worker is running
     * outdated code (the server closed it with OUTDATED_VERSION) — the
     * OUTDATED signal, so even a late/lazy tab taking the older-startTs early
     * return renounces main-tab duties and surfaces the reload notice.
     *
     * @param {MessagePort} client
     */
    _finishClientInitialization(client) {
        this.sendToClient(client, "BUS:WORKER_STATE_UPDATED", this.state);
        this.sendToClient(client, "BUS:INITIALIZED");
        if (!this.active) {
            this.sendToClient(client, "BUS:OUTDATED");
        }
    }

    /**
     * Determine whether or not the websocket associated to this worker
     * is connected.
     *
     * @returns {boolean}
     */
    _isWebsocketConnected() {
        return (
            this.websocket && this.websocket.readyState === WEBSOCKET_READY_STATE.OPEN
        );
    }

    /**
     * Determine whether or not the websocket associated to this worker
     * is connecting.
     *
     * @returns {boolean}
     */
    _isWebsocketConnecting() {
        return (
            this.websocket &&
            this.websocket.readyState === WEBSOCKET_READY_STATE.CONNECTING
        );
    }

    /**
     * Determine whether or not the websocket associated to this worker
     * is in the closing state.
     *
     * @returns {boolean}
     */
    _isWebsocketClosing() {
        return (
            this.websocket &&
            this.websocket.readyState === WEBSOCKET_READY_STATE.CLOSING
        );
    }

    /**
     * Triggered when a connection is closed. If closure was not clean ,
     * try to reconnect after indicating to the clients that the
     * connection was closed.
     *
     * @param {CloseEvent} ev
     * @param {number} code  close code indicating why the connection
     * was closed.
     * @param {string} reason reason indicating why the connection was
     * closed.
     */
    _onWebsocketClose(ev) {
        if (this._isStaleSocketEvent(ev)) {
            return;
        }
        const { code, reason } = ev;
        clearInterval(this._connectionCheckInterval);
        this._logDebug("_onWebsocketClose", code, reason);
        this._updateState(CONNECTION_STATE.DISCONNECTED);
        // Flush any callback chained on this connection's subscribe gate:
        // non-subscribe messages sent while the socket was open (but before its
        // first subscribe went out) wait on it. Resolving is safe — the chained
        // callback re-checks `_isWebsocketConnected()` (false here) and
        // re-queues into `messageWaitQueue` for the next open. No replacement
        // gate is needed: the next `_start` brings a fresh Connection with its
        // own, and `lastSubscription` dies with this connection too.
        this._connection?.subscribeDeferred.resolve();
        if (
            [
                WEBSOCKET_CLOSE_CODES.KEEP_ALIVE_TIMEOUT,
                WEBSOCKET_CLOSE_CODES.CLOSING_HANDSHAKE_ABORTED,
            ].includes(code)
        ) {
            // Don't wait to reconnect: keep-alive shouldn't be noticed, and the
            // closing handshake was aborted because the client explicitly tried
            // to connect while the socket was stuck in the closing state.
            this.connectRetryDelay = 0;
        }
        if (this.isReconnecting) {
            // Connection was not established but the close event was
            // triggered anyway. Let the onWebsocketError method handle
            // this case.
            return;
        }
        this.broadcast("BUS:DISCONNECT", { code, reason });
        if (code === WEBSOCKET_CLOSE_CODES.CLEAN) {
            if (reason === "OUTDATED_VERSION") {
                console.warn("Worker deactivated due to an outdated version.");
                this.active = false;
                this.broadcast("BUS:OUTDATED");
            }
            // WebSocket was closed on purpose, do not try to reconnect.
            return;
        }
        // WebSocket was not closed cleanly, let's try to reconnect.
        this.broadcast("BUS:RECONNECTING", { closeCode: code });
        this.isReconnecting = true;
        if (code === WEBSOCKET_CLOSE_CODES.SESSION_EXPIRED) {
            this.isWaitingForNewUID = true;
        }
        this._retryConnectionWithDelay();
    }

    /**
     * Whether ``ev`` was fired by a socket that a newer connection has already
     * superseded. A real DOM event carries its socket as ``currentTarget``;
     * when that is not the current connection's socket, the event is a late
     * straggler from a replaced socket and must be ignored. Synthetic events
     * (built by ``_start`` for the current connection, with no ``currentTarget``)
     * are trusted.
     *
     * @param {Event} [ev]
     * @returns {boolean}
     */
    _isStaleSocketEvent(ev) {
        const target = ev?.currentTarget;
        if (target && target !== this.websocket) {
            this._logDebug("ignoring stale socket event", ev.type);
            return true;
        }
        return false;
    }

    /**
     * Triggered when a connection failed or failed to established.
     *
     * @param {Event} [ev]
     */
    _onWebsocketError(ev) {
        if (this._isStaleSocketEvent(ev)) {
            return;
        }
        this._logDebug("_onWebsocketError");
        this._retryConnectionWithDelay();
    }

    /**
     * Handle data received from the bus.
     *
     * @param {MessageEvent} messageEv
     */
    _onWebsocketMessage(messageEv) {
        if (this._isStaleSocketEvent(messageEv)) {
            return;
        }
        this._restartConnectionCheckInterval();
        let payload;
        try {
            payload = JSON.parse(messageEv.data);
        } catch {
            // The server delivers notification batches as JSON. Anything else
            // (e.g. an echoed keepalive/control frame) is not ours: ignore it
            // rather than throwing out of the message listener.
            this._logDebug("_onWebsocketMessage: ignored non-JSON frame");
            return;
        }
        if (!Array.isArray(payload)) {
            // The server delivers notification batches as a JSON array. A frame
            // that is valid JSON but not an array (e.g. an echoed control frame)
            // is not a notification batch: ignore it rather than throwing out of
            // the message listener on `payload.filter`.
            this._logDebug("_onWebsocketMessage: ignored non-array frame");
            return;
        }
        // Drop any notification whose EXACT id was already processed. This
        // deliberately mirrors the server's own dedup semantics
        // (`NotificationDispatchState` in bus/websocket.py): notifications
        // committed out of id order by concurrent transactions are
        // re-delivered with LOWER ids in LATER batches during a hold-back
        // window (`MAX_NOTIFICATION_HISTORY_SEC`). A monotonic
        // `id > lastNotificationId` watermark would silently discard exactly
        // those late-committed notifications; only an id-level seen check is
        // both duplicate-safe and loss-free.
        const now = Date.now();
        this._pruneSeenNotificationIds(now);
        const notifications = payload.filter(
            (notification) => !this.seenNotificationIds.has(notification.id),
        );
        this._logDebug("_onWebsocketMessage", notifications);
        if (!notifications.length) {
            return;
        }
        // Track the greatest id seen (batches are not guaranteed ascending),
        // used only as the `last` value of (re)subscribes. Max is correct
        // there: within a connection the server ignores later `last` values
        // (`initialize_last_id` only adopts it while its own last_id is 0)
        // and holds its `last_id` back server-side for out-of-order commits;
        // on a fresh connection the server adopts it as the polling floor,
        // and any held-back lower ids it re-sends are handled by the
        // seen-id filter above.
        //
        // A loop, NOT `Math.max(this.lastNotificationId, ...ids)`: the spread
        // passes one argument per notification and throws `RangeError: Maximum
        // call stack size exceeded` past ~130k of them. The server bounds a
        // batch now (`MAX_NOTIFICATIONS_PER_POLL`), but this side must not be
        // what breaks if that bound is ever raised -- and the failure was
        // silent, not a visible error.
        let highestId = this.lastNotificationId;
        for (const notification of notifications) {
            if (notification.id > highestId) {
                highestId = notification.id;
            }
        }
        // Broadcast BEFORE recording the ids as seen. Marking first meant that
        // anything throwing in between lost the batch outright: the ids were
        // remembered as delivered while no client had received them, so the
        // dedup filter discarded the server's redelivery too. Recording after
        // the broadcast can at worst repeat a batch, which subscribers already
        // tolerate; it can no longer swallow one.
        this.broadcast("BUS:NOTIFICATION", notifications);
        this.lastNotificationId = highestId;
        for (const notification of notifications) {
            this.seenNotificationIds.set(notification.id, now);
        }
    }

    /**
     * Forget seen notification ids that are older than the retention window
     * (they can no longer be legitimately re-sent by the server), and cap the
     * map size defensively.
     *
     * @param {number} now
     */
    _pruneSeenNotificationIds(now) {
        // Insertion order == arrival order, so expired entries form a prefix.
        for (const [id, seenAt] of this.seenNotificationIds) {
            if (
                now - seenAt <= this.SEEN_NOTIFICATION_RETENTION_MS &&
                this.seenNotificationIds.size <= this.SEEN_NOTIFICATION_MAX_COUNT
            ) {
                break;
            }
            this.seenNotificationIds.delete(id);
        }
    }

    async _logDebug(title, ...args) {
        if (this.loggingEnabled) {
            try {
                await logger.log({
                    dt: new Date().toISOString(),
                    event: title,
                    args,
                    worker: UUID,
                });
            } catch (e) {
                console.error(e);
            }
        }
    }

    /**
     * Triggered on websocket open. Send message that were waiting for
     * the connection to open.
     */
    _onWebsocketOpen(ev) {
        if (this._isStaleSocketEvent(ev)) {
            return;
        }
        this._logDebug("_onWebsocketOpen");
        // No deferred/subscription resets here: this is a fresh Connection (built
        // in `_start`), so its `subscribeDeferred` is unresolved and its
        // `lastSubscription` is null already. The open-time `_updateChannels`
        // below therefore always (re)subscribes and resolves the gate — the
        // "always subscribe on a fresh connection" invariant is structural now,
        // not restored by nulling worker fields.
        const connection = this._connection;
        this._updateState(CONNECTION_STATE.CONNECTED);
        this.broadcast(this.isReconnecting ? "BUS:RECONNECT" : "BUS:CONNECT");
        this._debouncedUpdateChannels();
        this.connectRetryDelay = this.INITIAL_RECONNECT_DELAY;
        // Actually cancel any pending retry, don't just drop the handle: an
        // orphaned timer would survive a later BUS:STOP (offline), fire,
        // reconnect the stopped worker, and — through the error path — re-arm
        // itself forever.
        clearTimeout(this.connectTimeout);
        this.connectTimeout = null;
        this.isReconnecting = false;
        connection.subscribeDeferred.then(() => {
            if (this._connection !== connection || !this._isWebsocketConnected()) {
                // Socket already closed/replaced: keep the queue for the next
                // open instead of writing to a dead or superseded socket.
                return;
            }
            // Flush the queued application messages after this connection's own
            // subscribe. No subscribe can be queued: `_updateChannels` only ever
            // subscribes while the socket is open (sending directly), so the
            // queue holds application messages only. Paced, not in one burst --
            // see FLUSH_CHUNK_SIZE.
            this._flushMessageQueue(connection);
        });
        this._restartConnectionCheckInterval();
    }

    /**
     * Send the messages queued while offline, in chunks small enough that the
     * server's incoming-frame rate limiter never trips (see FLUSH_CHUNK_SIZE).
     *
     * Messages are removed from the queue only as they are sent, so a socket
     * that dies mid-flush leaves the remainder queued for the next connection
     * instead of dropping it.
     *
     * @param {Connection} connection the connection this flush belongs to
     */
    _flushMessageQueue(connection) {
        this._flushTimeout = null;
        if (this._connection !== connection || !this._isWebsocketConnected()) {
            // Closed or superseded: keep what is left for the next open.
            return;
        }
        for (const message of this.messageWaitQueue.splice(0, this.FLUSH_CHUNK_SIZE)) {
            this.websocket.send(message);
        }
        if (this.messageWaitQueue.length) {
            this._flushTimeout = setTimeout(
                () => this._flushMessageQueue(connection),
                this.FLUSH_CHUNK_DELAY,
            );
        }
    }

    /**
     * Queue a message for the next connection, bounded by MESSAGE_QUEUE_MAX.
     *
     * @param {string} payload serialized message
     */
    _queueMessage(payload) {
        while (this.messageWaitQueue.length >= this.MESSAGE_QUEUE_MAX) {
            this.messageWaitQueue.shift();
            this._logDebug("message_queue_overflow: dropped oldest queued message");
        }
        this.messageWaitQueue.push(payload);
    }

    /**
     * Sends a custom application-level message to perform a connection check
     * on the WebSocket.
     *
     * Browsers rely on the OS's TCP mechanism, which can take minutes or
     * hours to detect a dead connection. Sending data triggers an immediate
     * I/O operation, quickly revealing any network-level failure. This must be
     * implemented at the application level because the browser WebSocket API
     * does not expose the built-in ping/pong mechanism.
     */
    _restartConnectionCheckInterval() {
        clearInterval(this._connectionCheckInterval);
        this._connectionCheckInterval = setInterval(() => {
            if (this._isWebsocketConnected()) {
                this.websocket.send(new Uint8Array([0x00]));
                this._logDebug("connection_checked");
            }
        }, this.CONNECTION_CHECK_DELAY);
    }

    /**
     * Try to reconnect to the server, after an exponential back off plus a
     * random spread proportional to it.
     *
     * The spread exists for the restart case: a bus process going down drops
     * every client on every database it serves at the same instant, they all
     * reconnect together, and each database that comes back triggers a registry
     * recompute server-side, so the recomputes pile up on the process that just
     * started. A spread of one second was far too narrow to break that wave up.
     *
     * It is proportional -- `min(base, RECONNECT_JITTER)` -- rather than a flat
     * window, because the two goals pull in opposite directions. A flat 30s
     * window (what upstream took) spreads the herd but also makes the *first*
     * retry take a median 16s, so one client's transient blip costs it sixteen
     * seconds of dead notifications instead of one and a half. Scaling the
     * spread to the attempt keeps the first retry where it was and widens the
     * window as attempts accumulate, which is when it is actually needed: a
     * restarting server refuses the early attempts anyway, and the pile-up
     * happens once clients start succeeding.
     */
    _retryConnectionWithDelay() {
        // Cancel any pending retry first: a failed connection fires both
        // `error` and `close`, each of which schedules a retry. Without this,
        // the first timer would be orphaned (untracked by `connectTimeout`,
        // so uncancellable by `_stop`), leaking a zombie reconnect.
        clearTimeout(this.connectTimeout);
        // `connectRetryDelay` is the jitter-free exponential base: keeping
        // jitter out of it stops the base from drifting and makes
        // MAXIMUM_RECONNECT_DELAY a true ceiling. Jitter is added only to the
        // armed timer. A base of 0 means "reconnect immediately" (set on
        // keep-alive/aborted closes) and skips jitter — but the base is then
        // advanced to INITIAL so a persistently failing socket backs off
        // normally instead of hot-looping at delay 0. Exponential growth only
        // starts from INITIAL: after the 0-delay fast path the next delay is
        // exactly INITIAL_RECONNECT_DELAY, not INITIAL * 1.5.
        const delay =
            this.connectRetryDelay === 0
                ? 0
                : this.connectRetryDelay +
                  Math.min(this.connectRetryDelay, this.RECONNECT_JITTER) *
                      Math.random();
        this.connectRetryDelay =
            this.connectRetryDelay === 0
                ? this.INITIAL_RECONNECT_DELAY
                : Math.min(this.connectRetryDelay * 1.5, MAXIMUM_RECONNECT_DELAY);
        this._logDebug("_retryConnectionWithDelay", delay);
        this.connectTimeout = setTimeout(this._start.bind(this), delay);
    }

    /**
     * Send a message to the server through the websocket connection.
     * If the websocket is not open, enqueue the message and send it
     * upon the next reconnection.
     *
     * @param {{event_name: string, data: any }} message Message to send to the server.
     */
    _sendToServer(message) {
        this._logDebug("_sendToServer", message);
        const payload = JSON.stringify(message);
        if (!this._isWebsocketConnected()) {
            // Not open: hold the message for the next connection's flush. Only
            // application messages ever reach here while offline — subscribes
            // are sent by `_updateChannels`, which no-ops unless the socket is
            // open, so nothing stale can pile up in the queue.
            this._queueMessage(payload);
            return;
        }
        if (message["event_name"] === "subscribe") {
            this.websocket.send(payload);
        } else {
            const connection = this._connection;
            connection.subscribeDeferred.then(() => {
                // The gate can resolve after the connection changed (e.g. this
                // connection closed): re-queue for the next open instead of
                // writing to a dead/superseded socket and losing the message.
                if (this._connection === connection && this._isWebsocketConnected()) {
                    this.websocket.send(payload);
                } else {
                    this._queueMessage(payload);
                }
            });
        }
        this._restartConnectionCheckInterval();
    }

    _removeWebsocketListeners() {
        this.websocket?.removeEventListener("open", this._onWebsocketOpen);
        this.websocket?.removeEventListener("message", this._onWebsocketMessage);
        this.websocket?.removeEventListener("error", this._onWebsocketError);
        this.websocket?.removeEventListener("close", this._onWebsocketClose);
    }

    /**
     * Start the worker by opening a websocket connection.
     */
    _start() {
        this._logDebug("_start");
        if (
            !this.active ||
            this._isWebsocketConnected() ||
            this._isWebsocketConnecting()
        ) {
            return;
        }
        this._removeWebsocketListeners();
        if (this._isWebsocketClosing()) {
            // The close event didn’t trigger. Trigger manually to maintain
            // correct state and lifecycle handling.
            const wasReconnecting = this.isReconnecting;
            // Synthetic close for the CURRENT connection (no `currentTarget`, so
            // it is not treated as a stale-socket event).
            this._onWebsocketClose(
                new CloseEvent("close", {
                    code: WEBSOCKET_CLOSE_CODES.CLOSING_HANDSHAKE_ABORTED,
                }),
            );
            this._connection = null;
            if (wasReconnecting) {
                // `_onWebsocketClose` early-returns while reconnecting because
                // it expects a real `error` event to drive the retry — but this
                // synthetic close has none. Schedule the retry explicitly so
                // the reconnect loop doesn't stall until an external BUS:START.
                this._retryConnectionWithDelay();
            }
            return;
        }
        const socket = new WebSocket(this.websocketURL);
        this._connection = new Connection(socket, ++this._epoch);
        this._updateState(CONNECTION_STATE.CONNECTING);
        socket.addEventListener("open", this._onWebsocketOpen);
        socket.addEventListener("error", this._onWebsocketError);
        socket.addEventListener("message", this._onWebsocketMessage);
        socket.addEventListener("close", this._onWebsocketClose);
    }

    /**
     * Stop the worker.
     */
    _stop() {
        this._logDebug("_stop");
        clearTimeout(this.connectTimeout);
        // `_stop` removes the socket listeners below, so `_onWebsocketClose`
        // (the other place clearing this interval) will not run: clear it here
        // to avoid leaking a timer on every stop cycle.
        clearInterval(this._connectionCheckInterval);
        // Same for a paced queue flush in progress: it targets the socket
        // this stop is tearing down.
        clearTimeout(this._flushTimeout);
        this._flushTimeout = null;
        // Cancel pending debounced work so it can't fire against the *next*
        // connection: a trailing `_updateChannels`/`_sendToServer` would act on
        // a socket this stop is tearing down.
        this._debouncedUpdateChannels.cancel();
        this._debouncedSendToServer.cancel();
        // Drop the pending force with the timer it belonged to: otherwise the
        // next connection's open-time update would inherit it and force a
        // subscribe that nothing asked for.
        this._forceNextUpdate = false;
        this.connectRetryDelay = this.INITIAL_RECONNECT_DELAY;
        this.isReconnecting = false;
        const connection = this._connection;
        const shouldBroadcastClose =
            connection && connection.socket.readyState !== WEBSOCKET_READY_STATE.CLOSED;
        connection?.socket.close();
        this._removeWebsocketListeners();
        // Drop the connection before resolving its gate: `_stop` removed the
        // socket listeners, so `_onWebsocketClose` (which resolves the gate and
        // reports DISCONNECTED) will not run. A pending send chained on the gate
        // would otherwise be orphaned; with the connection dropped it re-checks
        // `_isWebsocketConnected()` (false) and re-queues into `messageWaitQueue`.
        // Dropping it also stops `_initializeConnection` from reporting a live
        // connection to tabs opened while stopped. `lastSubscription` dies with
        // the connection, so the next connect re-subscribes.
        this._connection = null;
        connection?.subscribeDeferred.resolve();
        this._updateState(CONNECTION_STATE.DISCONNECTED);
        if (shouldBroadcastClose) {
            this.broadcast("BUS:DISCONNECT", { code: WEBSOCKET_CLOSE_CODES.CLEAN });
        }
    }

    /**
     * Update the channel subscription on the server. Ignore if the channels
     * did not change since the last subscription.
     *
     * @param {boolean} force Whether or not we should update the subscription
     * event if the channels haven't change since last subscription.
     */
    _updateChannels({ force = false } = {}) {
        if (!this._isWebsocketConnected()) {
            // Only subscribe on an open socket. While connecting/disconnected
            // there is nothing to do: the (re)connect's open handler runs
            // `_updateChannels` again with the current channels, so a channel
            // change made in the meantime is picked up there. This is why no
            // subscribe is ever queued (see `_sendToServer`).
            return;
        }
        const connection = this._connection;
        const allTabsChannels = this._getAllChannels();
        const allTabsChannelsString = JSON.stringify(allTabsChannels);
        if (force || allTabsChannelsString !== connection.lastSubscription) {
            connection.lastSubscription = allTabsChannelsString;
            this._sendToServer({
                event_name: "subscribe",
                data: { channels: allTabsChannels, last: this.lastNotificationId },
            });
            connection.subscribeDeferred.resolve();
        }
    }
    /**
     * Update the worker state and broadcast the new state to its clients.
     *
     * @param {CONNECTION_STATE[keyof CONNECTION_STATE]} newState
     */
    _updateState(newState) {
        this.state = newState;
        this.broadcast("BUS:WORKER_STATE_UPDATED", newState);
    }
}
