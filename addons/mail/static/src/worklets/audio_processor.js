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
            when the user's voice drops in volume mid-sentence.
     * @param {boolean} [param0.processorOptions.postAllTics] true if we need to postMessage at each tics, this prevents
            sending events to the main thread on all tics when not necessary.
     * @param {number} [param0.processorOptions.volumeThreshold] the minimum value for audio detection
     */
    constructor({
        processorOptions: {
            frequencyRange,
            minimumActiveCycles = 10,
            postAllTics,
            volumeThreshold = 0.3,
        },
    }) {
        super();

        // timing variables
        this.processInterval = 50; // how many ms between each computation
        this.minimumActiveCycles = minimumActiveCycles;
        this.intervalInFrames = (this.processInterval / 1000) * globalThis.sampleRate;
        this.nextUpdateFrame = this.processInterval;

        // process variables
        this.activityBuffer = 0;
        this.volumeThreshold = volumeThreshold;
        this.frequencyRange = frequencyRange || [80, 400];
        this.isAboveThreshold = false;
        this.postAllTics = postAllTics;
        this.volume = 0;
        this.wasAboveThreshold = undefined;
    }

    process(inputs, outputs, parameters) {
        const input = inputs[0];
        if (input.length < 1) {
            return;
        }
        const samples = input[0];

        // throttles down the processing tic rate
        this.nextUpdateFrame -= samples.length;
        if (this.nextUpdateFrame >= 0) {
            return true;
        }
        this.nextUpdateFrame += this.intervalInFrames;

        // computes volume and threshold
        const startIndex = _getFrequencyIndex(
            this.frequencyRange[0],
            globalThis.sampleRate,
            samples.length
        );
        const endIndex = _getFrequencyIndex(
            this.frequencyRange[1],
            globalThis.sampleRate,
            samples.length
        );
        let sum = 0;
        for (let i = startIndex; i < endIndex; ++i) {
            sum += samples[i];
        }
        // Normalizing the volume so that volume mostly fits in the [0,1] range.
        const preNormalizationVolume = sum / (endIndex - startIndex);
        const preLogarithmVolume = preNormalizationVolume * 50 + 1;
        if (preLogarithmVolume <= 0) {
            this.volume = 0;
        } else {
            this.volume = Math.log10(preLogarithmVolume);
        }

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

/**
 * @param {number} targetFrequency in Hz
 * @param {number} sampleRate the sample rate of the audio
 * @param {number} samplesSize amount of samples in the audio input
 * @returns {number} the index of the targetFrequency within samplesSize
 */
function _getFrequencyIndex(targetFrequency, sampleRate, samplesSize) {
    const index = Math.round((targetFrequency / (sampleRate / 2)) * samplesSize);
    return Math.min(Math.max(0, index), samplesSize);
}

globalThis.registerProcessor("audio-processor", ThresholdProcessor);
