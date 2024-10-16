class BiquadBandpassFilter {
    constructor(sampleRate, frequency, Q) {
        this.x1 = 0;
        this.x2 = 0;
        this.y1 = 0;
        this.y2 = 0;

        const w0 = 2 * Math.PI * (frequency / sampleRate);
        const cosW0 = Math.cos(w0);
        const sinW0 = Math.sin(w0);
        const alpha = sinW0 / (2 * Q);
        const a0 = 1 + alpha;

        this.b0 = alpha / a0;
        this.b1 = 0;
        this.b2 = -alpha / a0;
        this.a1 = (-2 * cosW0) / a0;
        this.a2 = (1 - alpha) / a0;
    }

    processSample(input) {
        const output =
            this.b0 * input +
            this.b1 * this.x1 +
            this.b2 * this.x2 -
            this.a1 * this.y1 -
            this.a2 * this.y2;

        this.x2 = this.x1;
        this.x1 = input;
        this.y2 = this.y1;
        this.y1 = output;

        return output;
    }
}

// This processor allows access to audio channels directly on the audio rendering thread.
// This can be useful for running possibly expensive audio monitoring or processing operations
// off the main thread.
class ThresholdProcessor extends globalThis.AudioWorkletProcessor {
    /**
     * @param {Object} param0 options
     * @param {Object} param0.processorOptions
     * @param {Array<number>} param0.processorOptions.frequencyRange array of two numbers that represent the range of
            frequencies that we want to monitor in hz.
     * @param {number} [param0.processorOptions.minimumActiveCycles] - how many cycles have to pass since the last time the
            threshold was exceeded to go back to inactive state. It prevents the microphone to shut down
            when the user's voice drops in volume mid-sentence. Time in ms = minimumActiveCycles * processInterval.
     * @param {boolean} [param0.processorOptions.postAllTics] true if we need to postMessage at each tics, this prevents
            sending events to the main thread on all tics when not necessary.
     * @param {number} [param0.processorOptions.volumeThreshold] the minimum value for audio detection
     * @param {{ boost, shift }} [param0.processorOptions.normalizationParameters]
     */
    constructor({
        processorOptions: {
            frequencyRange,
            minimumActiveCycles = 30,
            postAllTics,
            volumeThreshold = 0.3,
            processInterval = 50,
            normalizationParameters = { boost: 1, shift: 0.6 },
        },
    }) {
        super();

        // timing variables
        this.processInterval = processInterval; // how many ms between each computation
        this.minimumActiveCycles = minimumActiveCycles;
        this.intervalInFrames = (this.processInterval / 1000) * globalThis.sampleRate;
        this.nextUpdateFrame = this.processInterval;

        // process variables
        this.boost = normalizationParameters.boost;
        this.shift = normalizationParameters.shift;
        this.activityBuffer = 0;
        this.volumeThreshold = volumeThreshold;
        this.frequencyRange = frequencyRange || [80, 400];
        this.isAboveThreshold = false;
        this.postAllTics = postAllTics;
        this.volume = 0;
        this.wasAboveThreshold = undefined;
        const centerFrequency = (frequencyRange[0] + frequencyRange[1]) / 2;
        const bandwidth = frequencyRange[1] - frequencyRange[0];
        this.bandpassFilter = new BiquadBandpassFilter(
            globalThis.sampleRate,
            centerFrequency,
            centerFrequency / bandwidth
        );
    }

    process(inputs, outputs, parameters) {
        const input = inputs[0];
        if (input.length < 1) {
            return;
        }
        const samples = input[0];
        // filter frequencies
        const filteredSamples = new Float32Array(samples.length);
        for (let i = 0; i < samples.length; i++) {
            filteredSamples[i] = this.bandpassFilter.processSample(samples[i]);
        }
        // throttles down the processing tic rate
        this.nextUpdateFrame -= samples.length;
        if (this.nextUpdateFrame >= 0) {
            return true;
        }
        this.nextUpdateFrame += this.intervalInFrames;
        // root mean square (too get a normalized volume)
        let sumOfSquares = 0;
        for (const sample of filteredSamples) {
            sumOfSquares += sample * sample;
        }
        const rms = Math.sqrt(sumOfSquares / filteredSamples.length);
        // bias the volume for a better spread on the [0,1] range
        const k = 1 + this.boost;
        const v = Math.pow(rms, this.shift);
        this.volume = (k * v) / ((k - 1) * v + 1);

        if (this.volume >= this.volumeThreshold) {
            this.activityBuffer = this.minimumActiveCycles;
        } else if (this.volume < this.volumeThreshold && this.activityBuffer > 0) {
            this.activityBuffer--;
        }
        this.isAboveThreshold = this.activityBuffer > 0;

        if (this.wasAboveThreshold !== this.isAboveThreshold) {
            this.wasAboveThreshold = this.isAboveThreshold;
            this.port.postMessage({ volume: this.volume, isAboveThreshold: this.isAboveThreshold });
            return true;
        }
        this.postAllTics &&
            this.port.postMessage({ volume: this.volume, isAboveThreshold: this.isAboveThreshold });
        return true;
    }
}

globalThis.registerProcessor("audio-processor", ThresholdProcessor);
