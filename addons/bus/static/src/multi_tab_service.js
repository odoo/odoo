import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";
import { EventBus } from "@odoo/owl";

export const multiTabService = {
    start() {
        const FAST_TIMEOUT = 1000;
        const MASTER_TIMEOUT = 1500;
        const JITTER = 1000;

        const bus = new EventBus();
        const channel = new BroadcastChannel("master_election");
        const id = generateUniqueId();
        let unregistered = false;
        let masterId = null;
        let electionDeferred = new Deferred();
        let lastHeardFromMaster = Date.now();
        let electionTimeout;
        let heartbeatCheckInterval;
        let heartbeatInterval;
        let fastElectTimeout;

        window.addEventListener("pagehide", () => {
            if (!unregistered && masterId === id) {
                channel.postMessage({ type: "no_longer_main_tab", id: id });
                bus.trigger("no_longer_main_tab");
            }
        });

        const sanitizedOrigin = location.origin.replace(/:\/{0,2}/g, "_");
        const localStoragePrefix = `${this.name}.${sanitizedOrigin}.`;

        function generateLocalStorageKey(baseKey) {
            return localStoragePrefix + baseKey;
        }

        function getItemFromStorage(key, defaultValue) {
            const item = browser.localStorage.getItem(generateLocalStorageKey(key));
            try {
                return item ? JSON.parse(item) : defaultValue;
            } catch {
                return item;
            }
        }

        function setItemInStorage(key, value) {
            browser.localStorage.setItem(generateLocalStorageKey(key), JSON.stringify(value));
        }

        function becomeMaster() {
            clearAllTimeouts();
            setMasterId(id);
            channel.postMessage({ type: "become_main_tab", id: id });
            bus.trigger("become_main_tab");
            console.info("Multi-tab service: this tab is now the main tab.");
            setHeartbeatInterval();
        }

        function connect() {
            channel.postMessage({ type: "connect", id: id });
            setFastElectTimeout();
        }

        function setFastElectTimeout() {
            fastElectTimeout = setTimeout(() => {
                becomeMaster();
            }, FAST_TIMEOUT);
        }

        function clearAllTimeouts() {
            clearTimeout(electionTimeout);
            clearInterval(heartbeatCheckInterval);
            clearInterval(heartbeatInterval);
        }

        function setMasterId(id) {
            masterId = id;
            if (electionDeferred) {
                electionDeferred.resolve(id);
            }
        }

        function setElectionTimeout() {
            clearTimeout(electionTimeout);
            electionTimeout = setTimeout(() => {
                becomeMaster();
            }, JITTER);
        }

        function setHeartbeatCheckInterval() {
            clearInterval(heartbeatCheckInterval);
            heartbeatCheckInterval = setInterval(() => {
                if (Date.now() - lastHeardFromMaster > MASTER_TIMEOUT + JITTER) {
                    startElection();
                }
            }, MASTER_TIMEOUT);
        }

        function sendHeartbeat() {
            lastHeardFromMaster = Date.now();
            channel.postMessage({ type: "heartbeat", id: id });
        }

        function setHeartbeatInterval() {
            clearInterval(heartbeatInterval);
            channel.postMessage({ type: "heartbeat", id: id });
            heartbeatInterval = setInterval(() => {
                sendHeartbeat();
            }, MASTER_TIMEOUT / 3);
        }

        function startElection() {
            clearAllTimeouts();
            electionDeferred = new Deferred();
            channel.postMessage({ type: "election", id: id });
            bus.trigger("election");
            setElectionTimeout();
            setHeartbeatCheckInterval();
        }

        function generateUniqueId() {
            const randomSuffix = Math.floor(Math.random() * 1000);
            const uid = `${Date.now()}${randomSuffix}`;
            console.info(`Multi-tab service: generated unique ID for this tab: ${uid}`);
            return uid;
        }

        function unregister() {
            if (unregistered) {
                return;
            }
            unregistered = true;
            clearAllTimeouts();
            if (masterId === id) {
                channel.postMessage({ type: "no_longer_main_tab", id: id });
                bus.trigger("no_longer_main_tab");
            }
        }

        channel.onmessage = (e) => {
            if (unregistered) {
                return;
            }
            const msg = e.data;
            if (msg.type === "heartbeat") {
                lastHeardFromMaster = Date.now();
                if (msg.id === masterId) {
                    return;
                } else if (!masterId) {
                    setMasterId(msg.id);
                    clearTimeout(fastElectTimeout);
                } else if (masterId === id) {
                    if (msg.id > masterId) {
                        channel.postMessage({ type: "no_longer_main_tab", id: id });
                        bus.trigger("no_longer_main_tab");
                        masterId = msg.id;
                        clearTimeout(heartbeatInterval);
                        setHeartbeatCheckInterval();
                    }
                }
            } else if (msg.type === "election") {
                lastHeardFromMaster = Date.now();
                if (msg.id > id) {
                    clearTimeout(electionTimeout);
                    setHeartbeatCheckInterval();
                    setMasterId(msg.id);
                } else {
                    channel.postMessage({ type: "election", id: id });
                    setElectionTimeout();
                }
            } else if (msg.type === "no_longer_main_tab") {
                startElection();
            } else if (msg.type === "connect") {
                if (masterId === id) {
                    sendHeartbeat();
                }
            }
        };

        function onStorage({ key, newValue }) {
            if (key && key.includes(localStoragePrefix)) {
                // Only trigger the shared_value_updated event if the key is
                // related to this service/origin.
                const baseKey = key.replace(localStoragePrefix, "");
                bus.trigger("shared_value_updated", { key: baseKey, newValue });
            }
        }

        browser.addEventListener("storage", onStorage);
        connect();
        setHeartbeatCheckInterval();

        return {
            bus,
            get currentTabId() {
                return id;
            },
            async isOnMainTab() {
                if (masterId) {
                    return masterId === id;
                }
                await electionDeferred;
                return masterId === id;
            },
            /**
             * Get value shared between all the tabs.
             *
             * @param {string} key
             * @param {any} defaultValue Value to be returned if this
             * key does not exist.
             */
            getSharedValue(key, defaultValue) {
                return getItemFromStorage(key, defaultValue);
            },
            /**
             * Set value shared between all the tabs.
             *
             * @param {string} key
             * @param {any} value
             */
            setSharedValue(key, value) {
                if (value === undefined) {
                    return this.removeSharedValue(key);
                }
                setItemInStorage(key, value);
            },
            /**
             * Remove value shared between all the tabs.
             *
             * @param {string} key
             */
            removeSharedValue(key) {
                browser.localStorage.removeItem(generateLocalStorageKey(key));
            },
            /**
             * Unregister this tab from the multi-tab service. It will no longer
             * be able to become the main tab.
             */
            unregister: unregister,
        };
    },
};

registry.category("services").add("multi_tab", multiTabService);
