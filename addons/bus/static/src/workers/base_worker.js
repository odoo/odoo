export class BaseWorker {
    constructor(name) {
        this.name = name;
        this.client = null; // only for testing purposes
    }

    handleMessage(event) {
        const { action } = event.data;
        if (action === "BASE:INIT") {
            if (this.name.includes("shared")) {
                event.target.postMessage({ type: "BASE:INITIALIZED" });
            } else {
                (this.client || globalThis).postMessage({ type: "BASE:INITIALIZED" });
            }
        }
    }
}
