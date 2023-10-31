/** @odoo-module **/

// Broad human voice range of frequencies in hz.
const HUMAN_VOICE_FREQUENCY_RANGE = [80, 1000];

//------------------------------------------------------------------------------
// Public
//------------------------------------------------------------------------------

/**
 * monitors the activity of an audio mediaStreamTrack
 *
 * @param {MediaStreamTrack} track
 * @param {Object} [processorOptions] options for the audio processor
 * @param {Array<number>} [processorOptions.frequencyRange] the range of frequencies to monitor in hz
 * @param {number} [processorOptions.minimumActiveCycles] how many cycles have to pass since the
 *          last time the threshold was exceeded to go back to inactive state, this prevents
 *          stuttering when the speech volume oscillates around the threshold value.
 * @param {function(boolean):void} [processorOptions.onThreshold] a function to be called when the threshold is passed
 * @param {function(number):void} [processorOptions.onTic] a function to be called at each tics
 * @param {number} [processorOptions.volumeThreshold] the normalized minimum value for audio detection
 * @returns {Object} returnValue
 * @returns {function} returnValue.disconnect callback to cleanly end the monitoring
 */
export async function monitorAudio(track, processorOptions) {
    // cloning the track so it is not affected by the enabled change of the original track.
    const monitoredTrack = track.clone();
    monitoredTrack.enabled = true;
    const stream = new window.MediaStream([monitoredTrack]);
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) {
        throw 'missing audio context';
    }
    const audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(stream);

    let processor;
    try {
        processor = await _loadAudioWorkletProcessor(source, audioContext, processorOptions);
    } catch (e) {
        // In case Worklets are not supported by the browser (eg: Safari)
        processor = _loadScriptProcessor(source, audioContext, processorOptions);
    }

    return async () => {
        processor.disconnect();
        source.disconnect();
        monitoredTrack.stop();
        try {
            await audioContext.close();
        } catch (e) {
            if (e.name === 'InvalidStateError') {
                return; // the audio context is already closed
            }
            throw e;
        }
    }
}

//------------------------------------------------------------------------------
// Private
//------------------------------------------------------------------------------

/**
 * @param {MediaStreamSource} source
 * @param {AudioContext} audioContext
 * @param {Object} [param2] options
 * @returns {Object} returnValue
 * @returns {function} returnValue.disconnect disconnect callback
 */
function _loadScriptProcessor(source, audioContext, { frequencyRange = HUMAN_VOICE_FREQUENCY_RANGE, minimumActiveCycles = 10, onThreshold, onTic, volumeThreshold = 0.3 } = {}) {
    // audio setup
    const bitSize = 1024;
    const analyser = audioContext.createAnalyser();
    source.connect(analyser);
    const scriptProcessorNode = audioContext.createScriptProcessor(bitSize, 1, 1);
    analyser.connect(scriptProcessorNode);
    analyser.fftsize = bitSize;
    scriptProcessorNode.connect(audioContext.destination);

    // timing variables
    const processInterval = 50; // how many ms between each computation
    const intervalInFrames = processInterval / 1000 * analyser.context.sampleRate;
    let nextUpdateFrame = processInterval;

    // process variables
    let activityBuffer = 0;
    let wasAboveThreshold = undefined;
    let isAboveThreshold = false;

    scriptProcessorNode.onaudioprocess = () => {
        // throttles down the processing tic rate
        nextUpdateFrame -= bitSize;
        if (nextUpdateFrame >= 0) {
            return;
        }
        nextUpdateFrame += intervalInFrames;

        // computes volume and threshold
        const normalizedVolume = getFrequencyAverage(analyser, frequencyRange[0], frequencyRange[1]);
        if (normalizedVolume >= volumeThreshold) {
            activityBuffer = minimumActiveCycles;
        } else if (normalizedVolume < volumeThreshold && activityBuffer > 0) {
            activityBuffer--;
        }
        isAboveThreshold = activityBuffer > 0;

        onTic && onTic(normalizedVolume);
        if (wasAboveThreshold !== isAboveThreshold) {
            wasAboveThreshold = isAboveThreshold;
            onThreshold && onThreshold(isAboveThreshold);
        }
    };
    return {
        disconnect: () => {
            analyser.disconnect();
            scriptProcessorNode.disconnect();
            scriptProcessorNode.onaudioprocess = null;
        },
    };
}

/**
 * @param {MediaStreamSource} source
 * @param {AudioContext} audioContext
 * @param {Object} [param2] options
 * @returns {Object} returnValue
 * @returns {function} returnValue.disconnect disconnect callback
 */
async function _loadAudioWorkletProcessor(source, audioContext, { frequencyRange = HUMAN_VOICE_FREQUENCY_RANGE, minimumActiveCycles = 10, onThreshold, onTic, volumeThreshold = 0.3 } = {}) {
    await audioContext.resume();
    // Safari does not support Worklet.addModule
    await audioContext.audioWorklet.addModule('/mail/rtc/audio_worklet_processor');
    const thresholdProcessor = new window.AudioWorkletNode(audioContext, 'audio-processor', {
        processorOptions: {
            minimumActiveCycles,
            volumeThreshold,
            frequencyRange,
            postAllTics: !!onTic,
        }
    });
    source.connect(thresholdProcessor);
    thresholdProcessor.port.onmessage = (event) => {
        const { isAboveThreshold, volume } = event.data;
        onThreshold && isAboveThreshold !== undefined && onThreshold(isAboveThreshold);
        onTic && volume !== undefined && onTic(volume);
    };
    return {
        disconnect: () => {
            thresholdProcessor.disconnect();
        },
    };
}

/**
 * @param {AnalyserNode} analyser
 * @param {number} lowerFrequency lower bound for relevant frequencies to monitor
 * @param {number} higherFrequency upper bound for relevant frequencies to monitor
 * @returns {number} normalized [0...1] average quantity of the relevant frequencies
 */
function getFrequencyAverage(analyser, lowerFrequency, higherFrequency) {
    const frequencies = new window.Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(frequencies);
    const sampleRate = analyser.context.sampleRate;
    const startIndex = _getFrequencyIndex(lowerFrequency, sampleRate, analyser.frequencyBinCount);
    const endIndex = _getFrequencyIndex(higherFrequency, sampleRate, analyser.frequencyBinCount);
    const count = endIndex - startIndex;
    let sum = 0;
    for (let index = startIndex; index < endIndex; index++) {
        sum += frequencies[index] / 255;
    }
    if (!count) {
        return 0;
    }
    return sum / count;
}

/**
 * @param {number} targetFrequency in Hz
 * @param {number} sampleRate the sample rate of the audio
 * @param {number} binCount AnalyserNode.frequencyBinCount
 * @returns {number} the index of the targetFrequency within binCount
 */
function _getFrequencyIndex(targetFrequency, sampleRate, binCount) {
    const index = Math.round(targetFrequency / (sampleRate / 2) * binCount);
    return Math.min(Math.max(0, index), binCount);
}
