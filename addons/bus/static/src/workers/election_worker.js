import { debounce, Deferred } from "@bus/workers/websocket_worker_utils";

export class ElectionWorker {
    MAIN_TAB_TIMEOUT_PERIOD = 3000;

    constructor() {
        this.masterTab = null;
        this.candidates = new Set();
        this.lastHeartbeat = Date.now();
        this.electionDeferred = null;
        this.heartbeatCheckInterval = null;
        this.heartbeatRequestInterval = null;
        this.debouncedReturnMasterId = debounce(this.returnMasterId.bind(this), 300);
    }

    registerCandidate(messagePort) {
        this.candidates.add(messagePort);
        console.log("ElectionWorker registered client:", messagePort);
        if (this.candidates.size === 1) {
            this.startElection();
        }
    }

    unregisterCandidate(messagePort) {
        if (this.candidates.has(messagePort)) {
            this.candidates[messagePort].close();
            delete this.candidates[messagePort];
            console.log("ElectionWorker unregistered client:", messagePort);
        } else {
            console.warn("Client not found for unregistration:", messagePort);
        }
    }

    electionBroadcast(message) {
        for (const candidate of this.candidates) {
            candidate.postMessage(message);
        }
    }

    requestHeartbeat(messagePort) {
        if (messagePort) {
            messagePort.postMessage({
                type: "ELECTION:HEARTBEAT_REQUEST",
            });
        } else {
            this.electionBroadcast({
                type: "ELECTION:HEARTBEAT_REQUEST",
            });
        }
    }

    async returnMasterId() {
        if (!this.electionDeferred && this.masterTab) {
            this.electionDeferred = new Deferred();
            this.requestHeartbeat(this.masterTab);
        }
        await this.electionDeferred;
        for (const candidate of this.candidates) {
            const answer = this.masterTab === candidate;
            candidate.postMessage({
                type: "ELECTION:MASTER_ID_RESPONSE",
                data: {
                    answer,
                },
            });
        }
    }

    startElection() {
        this.masterTab = null;
        clearInterval(this.heartbeatCheckInterval);
        clearInterval(this.heartbeatRequestInterval);
        if (!this.electionDeferred) {
            this.electionDeferred = new Deferred();
        }
        console.log("ElectionWorker starting election");
        this.lastHeartbeat = Date.now();
        this.requestHeartbeat();
    }

    finishElection(messagePort) {
        console.log("ElectionWorker finishing election with client:", messagePort);
        this.masterTab = messagePort;
        messagePort.postMessage({
            type: "ELECTION:ASSIGN_MASTER",
        });
        this.electionDeferred.resolve();
        this.electionDeferred = null;
        this.heartbeatCheckInterval = setInterval(() => {
            const now = Date.now();
            console.log("ElectionWorker checking master tab heartbeat: ", now - this.lastHeartbeat);
            if (now - this.lastHeartbeat > this.MAIN_TAB_TIMEOUT_PERIOD) {
                console.log("Master tab heartbeat timeout, starting new election");
                this.startElection();
            }
        }, this.MAIN_TAB_TIMEOUT_PERIOD);
        this.heartbeatRequestInterval = setInterval(() => {
            this.requestHeartbeat(this.masterTab);
        }, this.MAIN_TAB_TIMEOUT_PERIOD / 2);
    }

    handleElectionMessage(event) {
        const { action, data } = event.data;
        if (!action?.startsWith("ELECTION:")) {
            return;
        }
        console.log("ElectionWorker received message:", action, data);
        switch (action) {
            case "ELECTION:REGISTER":
                this.registerCandidate(event.target);
                break;
            case "ELECTION:UNREGISTER":
                this.unregisterCandidate(event.target);
                break;
            case "ELECTION:IS_MASTER?":
                this.debouncedReturnMasterId();
                break;
            case "ELECTION:HEARTBEAT":
                if (this.masterTab === event.target) {
                    this.lastHeartbeat = Date.now();
                }
                if (this.electionDeferred) {
                    if (this.masterTab) {
                        this.electionDeferred.resolve();
                    } else {
                        this.finishElection(event.target);
                    }
                }
                break;
            default:
                console.warn("Unknown message action:", action);
        }
    }
}
