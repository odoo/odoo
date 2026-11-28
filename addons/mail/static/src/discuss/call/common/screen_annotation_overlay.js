import { StorePlugin } from "@mail/core/common/store_plugin";
import {
    INK_FADE_MS,
    INK_VISIBLE_MS,
    ScreenAnnotationPlugin,
} from "@mail/discuss/call/common/screen_annotation_plugin";

import { Component, onMounted, onWillUnmount, signal, types, usePlugin, useProps } from "@odoo/owl";

const LINE_WIDTH = 4;
const LABEL_FONT = "600 12px sans-serif";

/**
 * @param {number} age ms since the point was drawn
 * @returns {number} its opacity, between 0 and 1
 */
export function getInkOpacity(age) {
    if (age <= INK_VISIBLE_MS) {
        return 1;
    }
    return Math.max(0, 1 - (age - INK_VISIBLE_MS) / INK_FADE_MS);
}

/**
 * Canvas laid over a shared screen: it shows the vanishing ink of every participant and, in
 * drawing mode, turns the pointer moves into strokes.
 */
export class ScreenAnnotationOverlay extends Component {
    static template = "discuss.ScreenAnnotationOverlay";

    canvas = signal.ref();
    store = usePlugin(StorePlugin);
    annotation = usePlugin(ScreenAnnotationPlugin);

    setup() {
        super.setup();
        this.props = useProps({
            session: types.instanceOf(this.store["discuss.channel.rtc.session"]),
        });
        this.animationFrame = undefined;
        this.isPointerDown = false;
        onMounted(() => {
            this.unsubscribe = this.annotation.subscribe((screenSessionId) => {
                if (screenSessionId === this.props.session.id) {
                    this.requestDraw();
                }
            });
            this.resizeObserver = new ResizeObserver(() => this.requestDraw());
            this.resizeObserver.observe(this.canvas());
            this.requestDraw();
        });
        onWillUnmount(() => {
            this.unsubscribe?.();
            this.resizeObserver?.disconnect();
            cancelAnimationFrame(this.animationFrame);
            if (this.isPointerDown) {
                this.annotation.endLocalStroke();
            }
        });
    }

    get video() {
        return this.canvas()?.parentElement?.querySelector(
            ":scope > .o-discuss-CallParticipantVideo > video"
        );
    }

    /**
     * The area of the canvas where the shared frame is painted: the video element keeps the
     * frame ratio, with bars on the sides when the card has another ratio.
     *
     * @returns {{ left: number, top: number, width: number, height: number }|undefined} in CSS
     *  pixels, relative to the canvas
     */
    getFrameRect() {
        const canvas = this.canvas();
        const video = this.video;
        if (!canvas || !video) {
            return undefined;
        }
        const canvasRect = canvas.getBoundingClientRect();
        const videoRect = video.getBoundingClientRect();
        let width = videoRect.width;
        let height = videoRect.height;
        if (video.videoWidth && video.videoHeight) {
            const isCover = getComputedStyle(video).objectFit === "cover";
            const scale = (isCover ? Math.max : Math.min)(
                videoRect.width / video.videoWidth,
                videoRect.height / video.videoHeight
            );
            width = video.videoWidth * scale;
            height = video.videoHeight * scale;
        }
        if (!width || !height) {
            return undefined;
        }
        return {
            left: videoRect.left - canvasRect.left + (videoRect.width - width) / 2,
            top: videoRect.top - canvasRect.top + (videoRect.height - height) / 2,
            width,
            height,
        };
    }

    /**
     * @param {PointerEvent} ev
     * @param {Object} [options]
     * @param {boolean} [options.clamp] keep a point outside of the frame on its edge instead
     *  of ignoring it
     * @returns {{ x: number, y: number }|undefined} normalized to the shared frame
     */
    getFramePoint(ev, { clamp = false } = {}) {
        const frame = this.getFrameRect();
        if (!frame) {
            return undefined;
        }
        const canvasRect = this.canvas().getBoundingClientRect();
        let x = (ev.clientX - canvasRect.left - frame.left) / frame.width;
        let y = (ev.clientY - canvasRect.top - frame.top) / frame.height;
        if (clamp) {
            x = Math.min(1, Math.max(0, x));
            y = Math.min(1, Math.max(0, y));
        } else if (x < 0 || x > 1 || y < 0 || y > 1) {
            return undefined;
        }
        return { x, y };
    }

    /** @param {PointerEvent} ev */
    onPointerDown(ev) {
        if (!this.annotation.isDrawing || ev.button !== 0) {
            return;
        }
        const point = this.getFramePoint(ev);
        if (!point) {
            return;
        }
        ev.preventDefault();
        ev.currentTarget.setPointerCapture?.(ev.pointerId);
        this.isPointerDown = true;
        this.annotation.startLocalStroke(this.props.session.id, point.x, point.y);
    }

    /** @param {PointerEvent} ev */
    onPointerMove(ev) {
        if (!this.isPointerDown) {
            return;
        }
        const point = this.getFramePoint(ev, { clamp: true });
        if (point) {
            this.annotation.addLocalPoint(point.x, point.y);
        }
    }

    onPointerUp() {
        if (!this.isPointerDown) {
            return;
        }
        this.isPointerDown = false;
        this.annotation.endLocalStroke();
    }

    requestDraw() {
        if (this.animationFrame) {
            return;
        }
        this.animationFrame = requestAnimationFrame(() => {
            this.animationFrame = undefined;
            this.draw();
        });
    }

    draw() {
        const canvas = this.canvas();
        if (!canvas) {
            return;
        }
        const ratio = window.devicePixelRatio || 1;
        const width = Math.round(canvas.clientWidth * ratio);
        const height = Math.round(canvas.clientHeight * ratio);
        if (canvas.width !== width || canvas.height !== height) {
            canvas.width = width;
            canvas.height = height;
        }
        const ctx = canvas.getContext("2d");
        ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
        ctx.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);
        const now = performance.now();
        this.annotation.prune(now);
        const frame = this.getFrameRect();
        if (!frame) {
            return;
        }
        let hasInk = false;
        for (const stroke of this.annotation.getStrokes(this.props.session.id)) {
            hasInk = this.drawStroke(ctx, frame, stroke, now) || hasInk;
        }
        if (hasInk) {
            // Keep animating while some ink is still fading out.
            this.requestDraw();
        }
    }

    /**
     * @returns {boolean} whether something was drawn
     */
    drawStroke(ctx, frame, stroke, now) {
        const points = stroke.points;
        if (!points.length) {
            return false;
        }
        const toCanvas = (point) => [
            frame.left + point.x * frame.width,
            frame.top + point.y * frame.height,
        ];
        ctx.save();
        ctx.strokeStyle = stroke.color;
        ctx.fillStyle = stroke.color;
        ctx.lineWidth = LINE_WIDTH;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.shadowColor = stroke.color;
        ctx.shadowBlur = 6;
        if (points.length === 1) {
            const [x, y] = toCanvas(points[0]);
            ctx.globalAlpha = getInkOpacity(now - points[0].time);
            ctx.beginPath();
            ctx.arc(x, y, LINE_WIDTH / 2, 0, 2 * Math.PI);
            ctx.fill();
        }
        for (let i = 1; i < points.length; i++) {
            ctx.globalAlpha = getInkOpacity(now - points[i].time);
            ctx.beginPath();
            ctx.moveTo(...toCanvas(points[i - 1]));
            ctx.lineTo(...toCanvas(points[i]));
            ctx.stroke();
        }
        const last = points.at(-1);
        if (stroke.name && stroke.authorId !== this.store.rtc?.selfSession?.id) {
            this.drawLabel(ctx, stroke, toCanvas(last), getInkOpacity(now - last.time));
        }
        ctx.restore();
        return true;
    }

    /** Names the author next to the tip of the stroke. */
    drawLabel(ctx, stroke, [x, y], opacity) {
        ctx.globalAlpha = opacity;
        ctx.shadowBlur = 0;
        ctx.font = LABEL_FONT;
        const paddingX = 6;
        const width = ctx.measureText(stroke.name).width + paddingX * 2;
        const height = 18;
        const left = x + 8;
        const top = y + 8;
        ctx.fillStyle = stroke.color;
        ctx.beginPath();
        ctx.roundRect(left, top, width, height, 4);
        ctx.fill();
        ctx.fillStyle = "#fff";
        ctx.textBaseline = "middle";
        ctx.fillText(stroke.name, left + paddingX, top + height / 2);
    }
}
