const BATCH = 2048;

class PcmCaptureProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.buffer = new Float32Array(BATCH);
        this.filled = 0;
    }

    process(inputs) {
        const channel = inputs[0]?.[0];
        let offset = 0;
        while (channel && offset < channel.length) {
            const take = Math.min(channel.length - offset, BATCH - this.filled);
            this.buffer.set(channel.subarray(offset, offset + take), this.filled);
            this.filled += take;
            offset += take;
            if (this.filled === BATCH) {
                this.port.postMessage(this.buffer.slice(0));
                this.filled = 0;
            }
        }
        return true;
    }
}

registerProcessor("speech-pcm-capture", PcmCaptureProcessor);
