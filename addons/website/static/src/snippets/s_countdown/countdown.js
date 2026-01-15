import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { _t } from "@web/core/l10n/translation";
import { isCSSColor } from "@web/core/utils/colors";
import { verifyHttpsUrl } from "@website/utils/misc";

export class Countdown extends Interaction {
    static selector = ".s_countdown";
    dynamicContent = {
        ".s_countdown_canvas_wrapper": {
            "t-att-class": () => ({
                "d-flex": true,
                "justify-content-center": true,
            }),
        },
    };

    setup() {
        // Remove SVG previews (used to simulated canvas)
        this.el.querySelectorAll("svg").forEach((el) => el.parentNode.remove());

        this.wrapperEl = this.el.querySelector(".s_countdown_canvas_wrapper");
        this.hereBeforeTimerEnds = false;
        this.endAction = this.el.dataset.endAction;
        this.endTime = parseInt(this.el.dataset.endTime);
        this.size = parseInt(this.el.dataset.size);
        this.display = this.el.dataset.display;

        if (!this.display && this.el.dataset.bsDisplay) {
            // With the BS5 upgrade script of 16.0, countdowns' data-display may
            // have been converted to data-bs-display by mistake. This will fix
            // the DOM for good measures, maybe even allowing to remove this
            // code in a few years as hopefully all current countdowns will have
            // been removed or edited (or when a proper upgrade script in a
            // future version of Odoo will be made, if necessary). TODO.
            this.display = this.el.dataset.bsDisplay;
            delete this.el.dataset.bsDisplay;
            this.el.dataset.display = this.display;
        }

        this.defaultColor = "rgba(0, 0, 0, 0)";
        this.layout = this.el.dataset.layout;
        this.layoutBackground = this.el.dataset.layoutBackground;
        this.progressBarStyle = this.el.dataset.progressBarStyle;
        this.progressBarWeight = this.el.dataset.progressBarWeight;

        this.layoutBackgroundColor = this.ensureCSSColor(this.el.dataset.layoutBackgroundColor);
        this.progressBarColor = this.ensureCSSColor(this.el.dataset.progressBarColor);
        this.textColor = this.ensureCSSColor(this.el.dataset.textColor);

        this.onlyOneUnit = this.display === "d";
        this.width = this.size;
        if (this.layout === "boxes") {
            this.width /= 1.75;
        }
        this.initTimeDiff();

        this.render();

        this.setInterval = setInterval(this.render.bind(this), 1000);
    }

    destroy() {
        // The optional chaining is required because the queried element may not
        // exist anymore if the interaction target has just been deleted
        this.el.querySelector(".s_countdown_canvas_wrapper")?.classList.remove("d-none");
        clearInterval(this.setInterval);
        window.removeEventListener("resize", this.onResize);
    }

    /**
     * Ensures the input is a valid CSS color
     *
     * @param {string} color
     * @returns {string}
     */
    ensureCSSColor(color) {
        if (isCSSColor(color)) {
            return color;
        }
        return getCSSVariableValue(color, getHtmlStyle(document)) || this.defaultColor;
    }

    /**
     * Handles the action that should be executed once the countdown ends.
     */
    handleEndCountdownAction() {
        if (this.endAction === "redirect") {
            const redirectUrl = verifyHttpsUrl(this.el.dataset.redirectUrl) || "/";
            if (this.hereBeforeTimerEnds) {
                this.waitForTimeout(() => (window.location = redirectUrl), 500);
            } else {
                if (!this.el.querySelector(".s_countdown_end_redirect_message")) {
                    const container = this.el.querySelector(
                        ":scope > .container, :scope > .container-fluid, :scope > .o_container_small"
                    );
                    this.renderAt(
                        "website.s_countdown.end_redirect_message",
                        {
                            redirectUrl: redirectUrl,
                        },
                        container
                    );
                }
            }
        } else if (this.endAction === "message" || this.endAction === "message_no_countdown") {
            this.el.querySelector(".s_countdown_end_message")?.classList.remove("d-none");
        }
        this.registerCleanup(() =>
            this.el.querySelector(".s_countdown_end_message")?.classList.add("d-none")
        );
    }

    getDelta() {
        return this.endTime - Date.now() / 1000;
    }

    createCanvasWrapper() {
        const divEl = document.createElement("div");
        divEl.classList.add("s_countdown_canvas_flex");
        const canvasEl = document.createElement("canvas");
        canvasEl.classList.add("w-100");
        divEl.appendChild(canvasEl);
        return divEl;
    }

    /**
     * The timeDiff object will contains every visible time unit
     * which will each contain its related canvas, total step, label..
     */
    initTimeDiff() {
        const delta = this.getDelta();
        this.timeDiff = [];
        if (this.isUnitVisible("d") && !(this.onlyOneUnit && delta < 86400)) {
            const divEl = this.createCanvasWrapper();
            this.insert(divEl, this.wrapperEl);
            this.timeDiff.push({
                canvas: divEl,
                // There is no logical number of unit (total) on which day units
                // can be compared against, so we use an arbitrary number.
                total: 15,
                label: _t("Days"),
                nbSeconds: 86400,
            });
        }
        if (this.isUnitVisible("h") || (this.onlyOneUnit && delta < 86400 && delta > 3600)) {
            const divEl = this.createCanvasWrapper();
            this.insert(divEl, this.wrapperEl);
            this.timeDiff.push({
                canvas: divEl,
                total: 24,
                label: _t("Hours"),
                nbSeconds: 3600,
            });
        }
        if (this.isUnitVisible("m") || (this.onlyOneUnit && delta < 3600 && delta > 60)) {
            const divEl = this.createCanvasWrapper();
            this.insert(divEl, this.wrapperEl);
            this.timeDiff.push({
                canvas: divEl,
                total: 60,
                label: _t("Minutes"),
                nbSeconds: 60,
            });
        }
        if (this.isUnitVisible("s") || (this.onlyOneUnit && delta < 60)) {
            const divEl = this.createCanvasWrapper();
            this.insert(divEl, this.wrapperEl);
            this.timeDiff.push({
                canvas: divEl,
                total: 60,
                label: _t("Seconds"),
                nbSeconds: 1,
            });
        }
    }

    updateTimediff() {
        let delta = this.getDelta();
        this.isFinished = delta < 0;
        if (this.isFinished) {
            for (const unitData of this.timeDiff) {
                unitData.nb = 0;
            }
            return;
        }
        this.hereBeforeTimerEnds = true;
        for (const unitData of this.timeDiff) {
            unitData.nb = Math.floor(delta / unitData.nbSeconds);
            delta -= unitData.nb * unitData.nbSeconds;
        }
    }

    /**
     * @param {string} unit - either "d", "m", "h", or "s"
     * @returns {boolean}
     */
    isUnitVisible(unit) {
        return this.display.includes(unit);
    }

    get shouldHideCountdown() {
        return this.isFinished && this.el.classList.contains("hide-countdown");
    }

    /**
     * Draws the whole countdown, including one countdown for each time unit.
     */
    render() {
        if (this.onlyOneUnit && this.getDelta() < this.timeDiff[0].nbSeconds) {
            this.el.querySelector(".s_countdown_canvas_flex").remove();
            this.initTimeDiff();
        }
        this.updateTimediff();

        if (this.layout === "text") {
            const canvasEls = this.el.querySelectorAll(".s_countdown_canvas_flex");
            for (const canvasEl of canvasEls) {
                canvasEl.classList.add("d-none");
            }
            if (!this.textWrapperEl) {
                this.textWrapperEl = document.createElement("span");
                this.textWrapperEl.classList.add("s_countdown_text_wrapper", "d-none");
                this.textWrapperEl.textContent = _t("Countdown ends in");
                const spanEl = document.createElement("span");
                spanEl.classList.add("s_countdown_text", "ms-1");
                this.textWrapperEl.appendChild(spanEl);
                this.insert(this.textWrapperEl, this.wrapperEl);
            }
            this.textWrapperEl.classList.toggle("d-none", this.shouldHideCountdown);

            const countdownText = this.timeDiff.map((e) => e.nb + " " + e.label).join(", ");
            this.el.querySelector(".s_countdown_text").innerText = countdownText.toLowerCase();
        } else {
            for (const val of this.timeDiff) {
                const canvas = val.canvas.querySelector("canvas");
                const ctx = canvas.getContext("2d");
                const dpr = window.devicePixelRatio || 1;
                ctx.canvas.width = this.width * dpr;
                ctx.canvas.height = this.size * dpr;
                ctx.scale(dpr, dpr);
                this.clearCanvas(ctx);

                canvas.classList.toggle("d-none", this.shouldHideCountdown);
                if (this.shouldHideCountdown) {
                    continue;
                }

                // Draw canvas elements
                if (this.layoutBackground !== "none") {
                    this.drawBgShape(ctx, this.layoutBackground === "plain");
                }
                this.drawText(canvas, val.nb, val.label, this.layoutBackground === "plain");
                if (this.progressBarStyle === "surrounded") {
                    this.drawProgressBarBg(ctx, this.progressBarWeight === "thin");
                }
                if (this.progressBarStyle !== "none") {
                    this.drawProgressBar(ctx, val.nb, val.total, this.progressBarWeight === "thin");
                }
                val.canvas.classList.toggle("mx-1", this.layout === "boxes");
            }
        }

        if (this.isFinished) {
            clearInterval(this.setInterval);
            this.handleEndCountdownAction();
            // Re-render on resize when the countdown is finished.
            if (!this.onResize) {
                this.onResize = () => this.render();
                window.addEventListener("resize", this.onResize);
            }
        }
    }

    /**
     * @param {CanvasRenderingContext2D} ctx - Context of the canvas
     */
    clearCanvas(ctx) {
        ctx.clearRect(0, 0, this.size, this.size);
    }

    /**
     * @param {HTMLCanvasElement} canvas
     * @param {string} textNb - text to display in the center of the canvas, in big
     * @param {string} textUnit - text to display bellow `textNb` in small
     * @param {boolean} full - if true, the shape will be drawn up to the progressbar
     */
    drawText(canvas, textNb, textUnit, full = false) {
        const ctx = canvas.getContext("2d");
        const dpr = window.devicePixelRatio || 1;
        const nbSize = this.size / 4;
        ctx.font = `${nbSize}px Arial`;
        ctx.fillStyle = this.textColor;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(textNb, canvas.width / dpr / 2, canvas.height / dpr / 2);

        const unitSize = this.size / 12;
        ctx.font = `${unitSize}px Arial`;
        ctx.fillText(
            textUnit,
            canvas.width / dpr / 2,
            canvas.height / dpr / 2 + nbSize / 1.5,
            this.width
        );

        if (
            this.layout === "boxes" &&
            this.layoutBackground !== "none" &&
            this.progressBarStyle === "none"
        ) {
            let barWidth = this.size / (this.progressBarWeight === "thin" ? 31 : 10);
            if (full) {
                barWidth = 0;
            }
            ctx.beginPath();
            ctx.moveTo(barWidth, this.size / 2);
            ctx.lineTo(this.width - barWidth, this.size / 2);
            ctx.stroke();
        }
    }

    /**
     * @param {CanvasRenderingContext2D} ctx - Context of the canvas
     * @param {boolean} full - if true, the shape will be drawn up to the progressbar
     */
    drawBgShape(ctx, full = false) {
        ctx.fillStyle = this.layoutBackgroundColor;
        ctx.beginPath();
        if (this.layout === "circle") {
            let rayon = this.size / 2;
            if (this.progressBarWeight === "thin") {
                rayon -= full ? this.size / 29 : this.size / 15;
            } else {
                rayon -= full ? 0 : this.size / 10;
            }
            ctx.arc(this.size / 2, this.size / 2, rayon, 0, Math.PI * 2);
            ctx.fill();
        } else if (this.layout === "boxes") {
            let barWidth = this.size / (this.progressBarWeight === "thin" ? 31 : 10);
            if (full) {
                barWidth = 0;
            }

            ctx.fillStyle = this.layoutBackgroundColor;
            ctx.rect(barWidth, barWidth, this.width - barWidth * 2, this.size - barWidth * 2);
            ctx.fill();

            const gradient = ctx.createLinearGradient(0, this.width, 0, 0);
            gradient.addColorStop(0, "#ffffff24");
            gradient.addColorStop(1, this.layoutBackgroundColor);
            ctx.fillStyle = gradient;
            ctx.rect(barWidth, barWidth, this.width - barWidth * 2, this.size - barWidth * 2);
            ctx.fill();
            ctx.canvas.style.borderRadius = "8px";
        }
    }

    /**
     * @param {CanvasRenderingContext2D} ctx - Context of the canvas
     * @param {number} nbUnit - how many unit should fill progress bar
     * @param {number} totalUnit - number of unit to do a complete progress bar
     * @param {boolean} useThinLine - if true, the progress bar will be thiner
     */
    drawProgressBar(ctx, nbUnit, totalUnit, useThinLine) {
        ctx.strokeStyle = this.progressBarColor;
        ctx.lineWidth = useThinLine ? this.size / 35 : this.size / 10;
        if (this.layout === "circle") {
            ctx.beginPath();
            ctx.arc(
                this.size / 2,
                this.size / 2,
                this.size / 2 - this.size / 20,
                Math.PI / -2,
                Math.PI * 2 * (nbUnit / totalUnit) + Math.PI / -2
            );
            ctx.stroke();
        } else if (this.layout === "boxes") {
            ctx.lineWidth *= 2;
            let pc = (nbUnit / totalUnit) * 100;

            // Lines: Top(x1,y1,x2,y2) Right(x1,y1,x2,y2) Bottom(x1,y1,x2,y2) Left(x1,y1,x2,y2)
            const linesCoordFuncs = [
                (linePc) => [
                    0 + ctx.lineWidth / 2,
                    0,
                    ((this.width - ctx.lineWidth / 2) * linePc) / 25 + ctx.lineWidth / 2,
                    0,
                ],
                (linePc) => [
                    this.width,
                    0 + ctx.lineWidth / 2,
                    this.width,
                    ((this.size - ctx.lineWidth / 2) * linePc) / 25 + ctx.lineWidth / 2,
                ],
                (linePc) => [
                    this.width -
                        ((this.width - ctx.lineWidth / 2) * linePc) / 25 -
                        ctx.lineWidth / 2,
                    this.size,
                    this.width - ctx.lineWidth / 2,
                    this.size,
                ],
                (linePc) => [
                    0,
                    this.size - ((this.size - ctx.lineWidth / 2) * linePc) / 25 - ctx.lineWidth / 2,
                    0,
                    this.size - ctx.lineWidth / 2,
                ],
            ];
            while (pc > 0 && linesCoordFuncs.length) {
                const linePc = Math.min(pc, 25);
                const lineCoord = linesCoordFuncs.shift()(linePc);
                ctx.beginPath();
                ctx.moveTo(lineCoord[0], lineCoord[1]);
                ctx.lineTo(lineCoord[2], lineCoord[3]);
                ctx.stroke();
                pc -= linePc;
            }
        }
    }

    /**
     * @param {CanvasRenderingContext2D} ctx - Context of the canvas
     * @param {boolean} useThinLine
     */
    drawProgressBarBg(ctx, useThinLine) {
        ctx.strokeStyle = this.progressBarColor;
        ctx.globalAlpha = 0.2;
        ctx.lineWidth = useThinLine ? this.size / 35 : this.size / 10;
        if (this.layout === "circle") {
            ctx.beginPath();
            ctx.arc(this.size / 2, this.size / 2, this.size / 2 - this.size / 20, 0, Math.PI * 2);
            ctx.stroke();
        } else if (this.layout === "boxes") {
            ctx.lineWidth *= 2;

            // Lines: Top(x1,y1,x2,y2) Right(x1,y1,x2,y2) Bottom(x1,y1,x2,y2) Left(x1,y1,x2,y2)
            const points = [
                [0 + ctx.lineWidth / 2, 0, this.width, 0],
                [this.width, 0 + ctx.lineWidth / 2, this.width, this.size],
                [0, this.size, this.width - ctx.lineWidth / 2, this.size],
                [0, 0, 0, this.size - ctx.lineWidth / 2],
            ];
            while (points.length) {
                const point = points.shift();
                ctx.beginPath();
                ctx.moveTo(point[0], point[1]);
                ctx.lineTo(point[2], point[3]);
                ctx.stroke();
            }
        }
        ctx.globalAlpha = 1;
    }
}

registry.category("public.interactions").add("website.countdown", Countdown);
