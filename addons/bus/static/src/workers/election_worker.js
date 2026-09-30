import { Deferred } from "@bus/workers/bus_worker_utils";

export class ElectionWorker {
    MAIN_TAB_TIMEOUT_PERIOD = 3000;

    /** @type {Set<MessagePort>} */
    candidates = new Set();
    /** @type {Deferred|null} */
    electionDeferred = null;
    /** @type {number|null} */
    heartbeatRequestInterval = null;
    lastHeartbeat = Date.now();
    /** @type {Deferred|null} */
    masterReplyDeferred = null;
    /** @type {MessagePort|null} */
    masterTab = null;

    constructor() {
        setInterval(() => {
            if (Date.now() - this.lastHeartbeat > this.MAIN_TAB_TIMEOUT_PERIOD) {
                this.startElection();
            }
        }, this.MAIN_TAB_TIMEOUT_PERIOD);
    }

    requestHeartbeat(messagePort) {
        if (messagePort) {
            messagePort.postMessage({ type: "ELECTION:HEARTBEAT_REQUEST" });
            return;
        }
        for (const candidate of this.candidates) {
            candidate.postMessage({ type: "ELECTION:HEARTBEAT_REQUEST" });
        }
    }

    async ensureMasterPresence() {
        this.masterReplyDeferred ??= new Deferred();
        if (this.masterTab) {
            this.requestHeartbeat(this.masterTab);
        } else {
            this.startElection();
        }
        await this.masterReplyDeferred;
    }

    startElection() {
        clearInterval(this.heartbeatRequestInterval);
        this.masterTab?.postMessage({ type: "ELECTION:UNASSIGN_MASTER" });
        this.masterTab = null;
        this.electionDeferred ??= new Deferred();
        this.requestHeartbeat();
    }

    finishElection(messagePort) {
        this.masterTab = messagePort;
        messagePort.postMessage({ type: "ELECTION:ASSIGN_MASTER" });
        this.electionDeferred.resolve();
        this.electionDeferred = null;
        this.heartbeatRequestInterval = setInterval(
            () => this.requestHeartbeat(this.masterTab),
            this.MAIN_TAB_TIMEOUT_PERIOD / 2
        );
    }

    async handleMessage(event) {
        const { action } = event.data;
        if (!action?.startsWith("ELECTION:")) {
            return;
        }
        switch (action) {
            case "ELECTION:REGISTER":
                this.candidates.add(event.target);
                await this.electionDeferred;
                if (!this.masterTab) {
                    this.startElection();
                }
                break;
            case "ELECTION:UNREGISTER":
                this.candidates.delete(event.target);
                if (this.masterTab === event.target) {
                    this.startElection();
                }
                break;
            case "ELECTION:IS_MASTER?":
                await this.ensureMasterPresence();
                event.target.postMessage({
                    type: "ELECTION:IS_MASTER_RESPONSE",
                    data: { answer: this.masterTab === event.target },
                });
                break;
            case "ELECTION:HEARTBEAT":
                if (this.electionDeferred) {
                    this.finishElection(event.target);
                }
                if (this.masterTab === event.target) {
                    this.lastHeartbeat = Date.now();
                    this.masterReplyDeferred?.resolve();
                    this.masterReplyDeferred = null;
                }
                break;
            default:
                console.warn("Unknown message action:", action);
        }
    }
}
