/* @odoo-module */

class Encoder {
    constructor(config) {
        this.config = {
            sampleRate: 44100,
            bitRate: 128,
        };

        Object.assign(this.config, config);

        // eslint-disable-next-line no-undef
        this.mp3Encoder = new lamejs.Mp3Encoder(1, this.config.sampleRate, this.config.bitRate);

        // Audio is processed by frames of 1152 samples per audio channel
        // http://lame.sourceforge.net/tech-FAQ.txt
        this.maxSamples = 1152;

        this.samplesMono = null;
        this.clearBuffer();
    }

    /**
     * Clear active buffer
     */
    clearBuffer() {
        this.dataBuffer = [];
    }

    /**
     * Append new audio buffer to current active buffer
     * @param {Buffer} buffer
     */
    appendToBuffer(buffer) {
        this.dataBuffer.push(new Int8Array(buffer));
    }

    /**
     * Float current data to 16 bits PCM
     * @param {Float32Array} input
     * @param {Int16Array} output
     */
    floatTo16BitPCM(input, output) {
        for (let i = 0; i < input.length; i++) {
            const s = Math.max(-1, Math.min(1, input[i]));
            output[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }
    }

    /**
     * Convert buffer to proper format
     * @param {Array} arrayBuffer
     */
    convertBuffer(arrayBuffer) {
        const data = new Float32Array(arrayBuffer);
        const out = new Int16Array(arrayBuffer.length);
        this.floatTo16BitPCM(data, out);

        return out;
    }

    /**
     * Encode and append current buffer to dataBuffer
     * @param {Array} arrayBuffer
     */
    encode(arrayBuffer) {
        this.samplesMono = this.convertBuffer(arrayBuffer);
        let remaining = this.samplesMono.length;

        for (let i = 0; remaining >= 0; i += this.maxSamples) {
            const left = this.samplesMono.subarray(i, i + this.maxSamples);
            const mp3buffer = this.mp3Encoder.encodeBuffer(left);
            this.appendToBuffer(mp3buffer);
            remaining -= this.maxSamples;
        }
    }

    /**
     * Return full dataBuffer
     */
    finish() {
        this.appendToBuffer(this.mp3Encoder.flush());
        return this.dataBuffer;
    }
}

export default Encoder;
