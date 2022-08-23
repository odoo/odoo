/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { clear } from '@mail/model/model_field_command';
import { attr, one } from '@mail/model/model_field';

function drawAndBlurImageOnCanvas(image, blurAmount, canvas) {
    canvas.width = image.width;
    canvas.height = image.height;
    if (blurAmount === 0) {
        canvas.getContext('2d').drawImage(image, 0, 0, image.width, image.height);
        return;
    }
    canvas.getContext('2d').clearRect(0, 0, image.width, image.height);
    canvas.getContext('2d').save();
    // FIXME : Does not work on safari https://bugs.webkit.org/show_bug.cgi?id=198416
    canvas.getContext('2d').filter = `blur(${blurAmount}px)`;
    canvas.getContext('2d').drawImage(image, 0, 0, image.width, image.height);
    canvas.getContext('2d').restore();
}

registerModel({
    name: 'BlurManager',
    lifecycleHooks: {
        _willDelete() {
            this.video.removeEventListener('loadeddata', this._onVideoPlay);
            this.selfieSegmentation.reset();
            this.video.srcObject = null;
            if (this.rejectStreamPromise) {
                this.rejectStreamPromise(new Error(this.env._t('The blur manager was removed before the beginning of the blur process')));
            }
        },
    },
    recordMethods: {
        onRequestFrameTimerTimeout() {
            this._requestFrame();
        },
        /**
         * @private
         */
        _drawWithCompositing(image, compositeOperation) {
            this.canvas.getContext('2d').globalCompositeOperation = compositeOperation;
            this.canvas.getContext('2d').drawImage(image, 0, 0);
        },
        /**
         * @private
         */
        _onChangeBackgroundBlurAmountSetting() {
            this.selfieSegmentation.setOptions({
                backgroundBlur: this.userSetting.backgroundBlurAmount,
            });
        },
        /**
         * @private
         */
        _onChangeEdgeBlurAmountSetting() {
            this.selfieSegmentation.setOptions({
                edgeBlurAmount: this.userSetting.edgeBlurAmount,
            });
        },
        /**
         * @private
         */
        async _onChangeSrcStream() {
            this.video.srcObject = null;
            this.selfieSegmentation.reset();
            if (this.rejectStreamPromise) {
                this.rejectStreamPromise(new Error(this.env._t('The source stream was removed before the beginning of the blur process')));
            }
            if (!this.srcStream) {
                return;
            }
            let rejectStreamPromise;
            let resolveStreamPromise;
            this.update({
                isVideoDataLoaded: false,
                stream: new Promise((resolve, reject) => {
                    rejectStreamPromise = reject;
                    resolveStreamPromise = resolve;
                }),
                rejectStreamPromise,
                resolveStreamPromise,
            });
            this.video.srcObject = this.srcStream.webMediaStream;
            this.video.load();
            this.selfieSegmentation.setOptions({
                selfieMode: false,
                backgroundBlur: this.userSetting.backgroundBlurAmount,
                edgeBlur: this.userSetting.edgeBlurAmount,
                modelSelection: 1,
            });
            this.selfieSegmentation.onResults(this._onSelfieSegmentationResults);
            this.video.addEventListener('loadeddata', this._onVideoPlay);
            this.video.autoplay = true;
            Promise.resolve(this.video.play()).catch(()=>{});
        },
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
            if (!this.srcStream) {
                return;
            }
            if (!this.isVideoDataLoaded) {
                return;
            }
            await this.selfieSegmentation.send({ image: this.video });
            this.update({ frameRequestTimer: { doReset: true } });
        },
        /**
         * @private
         */
        _onSelfieSegmentationResults(results) {
            if (!this.exists()) {
                return;
            }
            drawAndBlurImageOnCanvas(
                results.image,
                this.userSetting.backgroundBlurAmount,
                this.canvasBlur,
            );
            this.canvas.width = this.canvasBlur.width;
            this.canvas.height = this.canvasBlur.height;
            drawAndBlurImageOnCanvas(
                results.segmentationMask,
                this.userSetting.edgeBlurAmount,
                this.canvasMask,
            );
            this.canvas.getContext('2d').save();
            this.canvas.getContext('2d').drawImage(
                results.image,
                0,
                0,
                this.canvas.width,
                this.canvas.height,
            );
            this._drawWithCompositing(
                this.canvasMask,
                'destination-in',
            );
            this._drawWithCompositing(
                this.canvasBlur,
                'destination-over',
            );
            this.canvas.getContext('2d').restore();
        },
        /**
         * @private
         */
        _onVideoPlay() {
            this.update({
                isVideoDataLoaded: true,
            });
            this._requestFrame();
        },
        /**
         * @private
         */
        _requestFrame() {
            window.requestAnimationFrame(async () => {
                if (!this.exists()) {
                    return;
                }
                await this._onFrame();
                this.resolveStreamPromise(this.canvasStream);
            });
        },
    },
    fields: {
        canvas: attr({
            default: document.createElement('canvas'),
        }),
        canvasBlur: attr({
            default: document.createElement('canvas'),
        }),
        canvasMask: attr({
            default: document.createElement('canvas'),
        }),
        canvasStream: one('MediaStream', {
            compute() {
                if (this.srcStream) {
                    this.canvas.getContext('2d'); // canvas.captureStream() doesn't work on firefox before getContext() is called.
                    const webMediaStream = this.canvas.captureStream();
                    return { webMediaStream, id: webMediaStream.id };
                }
                return clear();
            },
            isCausal: true,
        }),
        frameRequestTimer: one('Timer', {
            inverse: 'blurManagerOwnerAsFrameRequest',
            isCausal: true,
        }),
        isVideoDataLoaded: attr({
            default: false,
        }),
        /**
         * promise reject function of this.stream promise
         */
        rejectStreamPromise: attr(),
        /**
         * promise resolve function of this.stream promise
         */
        resolveStreamPromise: attr(),
        rtc: one('Rtc', {
            identifying: true,
            inverse: 'blurManager',
        }),
        selfieSegmentation: attr({
            default: new window.SelfieSegmentation({
                locateFile: (file) => {
                    return `https://cdn.jsdelivr.net/npm/@mediapipe/selfie_segmentation@0.1/${file}`;
                },
            }),
        }),
        /**
         * mail.MediaStream, source stream for which the blur effect is computed.
         */
        srcStream: one('MediaStream', {
            isCausal: true,
        }),
        /**
         * Promise or undefined, based on this.srcStream, resolved when selfieSegmentation has started painting on the canvas,
         * resolves into a web.MediaStream that is the blurred version of this.srcStream.
         */
        stream: attr(),
        userSetting: one('UserSetting', {
            related: 'messaging.userSetting',
        }),
        video: attr({
            default: document.createElement('video'),
        }),
    },
    onChanges: [
        {
            dependencies: ['userSetting.edgeBlurAmount'],
            methodName: '_onChangeEdgeBlurAmountSetting',
        },
        {
            dependencies: ['userSetting.backgroundBlurAmount'],
            methodName: '_onChangeBackgroundBlurAmountSetting',
        },
        {
            dependencies: ['srcStream'],
            methodName: '_onChangeSrcStream',
        },
    ],
});
