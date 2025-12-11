import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { _t } from "@web/core/l10n/translation";
import { isCSSColor } from "@web/core/utils/colors";
import { verifyHttpsUrl } from "@website/utils/misc";

export class Countdown extends Interaction {
    static selector = ".s_countdown";
    dynamicContent = {
        ".s_countdown_wrapper": {
            "t-att-class": () => ({
                "d-flex": true,
                "justify-content-center": true,
            }),
        },
    };

    setup() {
        // Remove SVG previews (used to simulated canvas)
        this.el.querySelectorAll("svg").forEach((el) => el.parentNode.remove());

        this.wrapperEl = this.el.querySelector(".s_countdown_wrapper");
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

        this.onlyOneUnit = this.display === "d";
        this.width = this.size;
        this.initTimeDiff();

        this.render();
        this.setInterval = setInterval(this.render.bind(this), 1000);
    }

    destroy() {
        this.el.querySelector(".s_countdown_wrapper")?.classList.remove("d-none");
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

    get textColor() {
        return this.ensureCSSColor(getComputedStyle(this.el).color);
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
            // Only create canvas elements if we are using the circle layout
            const divEl = this.layout === "circle" ? this.createCanvasWrapper() : null;
            if (divEl) {
                this.insert(divEl, this.wrapperEl);
            }
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
            const divEl = this.layout === "circle" ? this.createCanvasWrapper() : null;
            if (divEl) {
                this.insert(divEl, this.wrapperEl);
            }
            this.timeDiff.push({
                canvas: divEl,
                total: 24,
                label: _t("Hours"),
                nbSeconds: 3600,
            });
        }
        if (this.isUnitVisible("m") || (this.onlyOneUnit && delta < 3600 && delta > 60)) {
            const divEl = this.layout === "circle" ? this.createCanvasWrapper() : null;
            if (divEl) {
                this.insert(divEl, this.wrapperEl);
            }
            this.timeDiff.push({
                canvas: divEl,
                total: 60,
                label: _t("Minutes"),
                nbSeconds: 60,
            });
        }
        if (this.isUnitVisible("s") || (this.onlyOneUnit && delta < 60)) {
            const divEl = this.layout === "circle" ? this.createCanvasWrapper() : null;
            if (divEl) {
                this.insert(divEl, this.wrapperEl);
            }
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
     * Isolates the first label letter to style correctly the "Compact" label style
     */
    wrapFirstLetter(string) {
        const firstLetter = string[0];
        const restOfString = string.slice(1);
        return `<span class="o_first_letter">${firstLetter}</span><span class="o_other_letters">${restOfString}</span>`;
    }
    /**
     * Draws the whole countdown, including one countdown for each time unit.
     */
    render() {
        if (this.onlyOneUnit && this.getDelta() < this.timeDiff[0].nbSeconds) {
            // In circle mode, we remove the canvas flex wrapper.
            // In text mode, the structure is different, but onlyOneUnit isn't usually combined with complex text templates in the same way.
            if (this.layout !== "text") {
                this.el.querySelector(".s_countdown_canvas_flex").remove();
            }
            this.initTimeDiff();
        }
        this.updateTimediff();

        // We toggle the wrapper visibility if the countdown is finished.
        this.wrapperEl?.classList.toggle("d-none", this.shouldHideCountdown);

        if (this.layout === "text") {
            this.countItemEls = this.el.querySelectorAll(".o_count_item");
            this.countItemNbsEls = this.el.querySelectorAll(".o_count_item_nbs");
            this.countItemNbEls = this.el.querySelectorAll(".o_count_item_nb");
            this.countItemLabelEls = this.el.querySelectorAll(".o_count_item_label");
            if (
                !this.countItemEls.length ||
                !this.countItemNbsEls.length ||
                !this.countItemLabelEls.length
            ) {
                return;
            }
            [...this.countItemEls].map((countItemEl) => countItemEl.classList.add("d-none"));
            for (const [index, metric] of this.timeDiff.entries()) {
                // Force to always have 2 numbers by metric
                metric.nb = String(metric.nb).padStart(2, "0");
                // If the selected template have inner element, wrap each number in each of them
                if (this.countItemNbEls.length > 0) {
                    metric.nb.split("").forEach((number, i) => {
                        this.countItemNbsEls[index].querySelectorAll("span")[i].textContent =
                            number;
                    });
                } else {
                    let itemNumber = this.countItemNbsEls[index];
                    while (itemNumber.firstElementChild) {
                        itemNumber = itemNumber.firstElementChild;
                    }
                    itemNumber.textContent = String(metric.nb).padStart(2, "0");
                }
                const labelEl = this.countItemLabelEls[index];
                const firstLetterEl = labelEl.querySelector(".o_first_letter");
                const otherLettersEl = labelEl.querySelector(".o_other_letters");
                if (firstLetterEl && otherLettersEl) {
                    if (firstLetterEl.textContent !== metric.label[0]) {
                        firstLetterEl.textContent = metric.label[0];
                    }
                    if (otherLettersEl.textContent !== metric.label.slice(1)) {
                        otherLettersEl.textContent = metric.label.slice(1);
                    }
                } else {
                    if (labelEl.textContent !== metric.label) {
                        labelEl.textContent = metric.label;
                    }
                }
                this.countItemEls[index].classList.remove("d-none");
            }
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
        }
        ctx.globalAlpha = 1;
    }
}

registry.category("public.interactions").add("website.countdown", Countdown);
