class AudioProcessor extends AudioWorkletProcessor {
    constructor(options) {
        super();
    }
    process(allInputs) {
        const inputs = allInputs[0][0];
        this.port.postMessage(inputs);
        return true;
    }
}
registerProcessor("processor", AudioProcessor);
