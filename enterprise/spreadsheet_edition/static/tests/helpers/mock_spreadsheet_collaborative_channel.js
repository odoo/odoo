export class MockSpreadsheetCollaborativeChannel {
    constructor() {
        this.listeners = [];
        this.pendingMessages = [];
        this.isConcurrent = false;
        this.serverRevisionId = "START_REVISION";
    }

    onNewMessage(id, callback) {
        this.leave(id);
        this.listeners.push({ id, callback });
    }

    leave(id) {
        this.listeners = this.listeners.filter((listener) => listener.id !== id);
    }

    sendMessage(message) {
        const msg = JSON.parse(JSON.stringify(message));
        switch (msg.type) {
            case "REMOTE_REVISION":
            case "REVISION_UNDONE":
            case "REVISION_REDONE":
                if (this.serverRevisionId === msg.serverRevisionId) {
                    this.serverRevisionId = msg.nextRevisionId;
                    this.broadcast(msg);
                }
                break;
            case "CLIENT_JOINED":
            case "CLIENT_LEFT":
            case "CLIENT_MOVED":
                this.broadcast(msg);
                break;
        }
    }

    async concurrent(concurrentExecutionCallback) {
        this.isConcurrent = true;
        await concurrentExecutionCallback();
        for (const message of this.pendingMessages) {
            this.notifyListeners(message);
        }
        this.isConcurrent = false;
        this.pendingMessages = [];
    }

    notifyListeners(message) {
        for (const { callback } of this.listeners) {
            callback(JSON.parse(JSON.stringify(message)));
        }
    }

    broadcast(message) {
        if (this.isConcurrent) {
            this.pendingMessages.push(message);
        } else {
            this.notifyListeners(message);
        }
    }
}
