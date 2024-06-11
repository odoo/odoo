/* @odoo-module */

import { closeStream } from "@mail/utils/common/misc";

import { browser } from "@web/core/browser/browser";

function drawAndBlurImageOnCanvas(image, blurAmount, canvas) {
    canvas.width = image.width;
    canvas.height = image.height;
    if (blurAmount === 0) {
        canvas.getContext("2d").drawImage(image, 0, 0, image.width, image.height);
        return;
    }
    canvas.getContext("2d").clearRect(0, 0, image.width, image.height);
    canvas.getContext("2d").save();
    // FIXME : Does not work on safari https://bugs.webkit.org/show_bug.cgi?id=198416
    canvas.getContext("2d").filter = `blur(${blurAmount}px)`;
    canvas.getContext("2d").drawImage(image, 0, 0, image.width, image.height);
    canvas.getContext("2d").restore();
}

export class BlurManager {
    canvas = document.createElement("canvas");
    canvasBlur = document.createElement("canvas");
    canvasMask = document.createElement("canvas");
    canvasStream;
    isVideoDataLoaded = false;
    rejectStreamPromise;
    resolveStreamPromise;
    selfieSegmentation = new window.SelfieSegmentation({
        locateFile: (file) => {
            return `https://cdn.jsdelivr.net/npm/@mediapipe/selfie_segmentation@0.1/${file}`;
        },
    });
    /**
     * Promise or undefined, based on the input stream, resolved when selfieSegmentation has started painting on the canvas,
     * resolves into a web.MediaStream that is the blurred version of the input stream.
     */
    stream;
    video = document.createElement("video");

    constructor(
        stream,
        { backgroundBlur = 10, edgeBlur = 10, modelSelection = 1, selfieMode = false } = {}
    ) {
        this.edgeBlur = edgeBlur;
        this.backgroundBlur = backgroundBlur;
        this._onVideoPlay = this._onVideoPlay.bind(this);
        this.video.addEventListener("loadeddata", this._onVideoPlay);
        this.canvas.getContext("2d"); // canvas.captureStream() doesn't work on firefox before getContext() is called.
        this.canvasStream = this.canvas.captureStream();
        let rejectStreamPromise;
        let resolveStreamPromise;
        Object.assign(this, {
            stream: new Promise((resolve, reject) => {
                rejectStreamPromise = reject;
                resolveStreamPromise = resolve;
            }),
            rejectStreamPromise,
            resolveStreamPromise,
        });
        this.video.srcObject = stream;
        this.video.load();
        this.selfieSegmentation.setOptions({
            selfieMode,
            modelSelection,
        });
        this.selfieSegmentation.onResults((r) => this._onSelfieSegmentationResults(r));
        this.video.autoplay = true;
        Promise.resolve(this.video.play()).catch(() => {});
    }

    close() {
        this.video.removeEventListener("loadeddata", this._onVideoPlay);
        this.video.srcObject = null;
        this.isVideoDataLoaded = false;
        this.selfieSegmentation.reset();
        closeStream(this.canvasStream);
        this.canvasStream = null;
        if (this.rejectStreamPromise) {
            this.rejectStreamPromise(
                new Error("The source stream was removed before the beginning of the blur process")
            );
        }
    }

    _drawWithCompositing(image, compositeOperation) {
        this.canvas.getContext("2d").globalCompositeOperation = compositeOperation;
        this.canvas.getContext("2d").drawImage(image, 0, 0);
    }

    /**
     * @private
     */
    _onVideoPlay() {
        this.isVideoDataLoaded = true;
        this._requestFrame();
    }

    /**
     * @private
     */
    async _onFrame() {
        if (!this.selfieSegmentation) {
            return;
        }
        if (!this.video) {
            return;
        }
        if (!this.isVideoDataLoaded) {
            return;
        }
        await this.selfieSegmentation.send({ image: this.video });
        browser.setTimeout(() => this._requestFrame(), Math.floor(1000 / 30)); // 30 fps
    }

    /**
     * @private
     */
    _onSelfieSegmentationResults(results) {
        drawAndBlurImageOnCanvas(results.image, this.backgroundBlur, this.canvasBlur);
        this.canvas.width = this.canvasBlur.width;
        this.canvas.height = this.canvasBlur.height;
        drawAndBlurImageOnCanvas(results.segmentationMask, this.edgeBlur, this.canvasMask);
        this.canvas.getContext("2d").save();
        this.canvas
            .getContext("2d")
            .drawImage(results.image, 0, 0, this.canvas.width, this.canvas.height);
        this._drawWithCompositing(this.canvasMask, "destination-in");
        this._drawWithCompositing(this.canvasBlur, "destination-over");
        this.canvas.getContext("2d").restore();
    }

    /**
     * @private
     */
    _requestFrame() {
        browser.requestAnimationFrame(async () => {
            await this._onFrame();
            this.resolveStreamPromise(this.canvasStream);
        });
    }
}
