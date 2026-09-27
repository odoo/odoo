import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { _t } from "@web/core/l10n/translation";
import { isCSSColor } from "@web/core/utils/colors";
import { verifyHttpsUrl } from "@website/utils/misc";

export class Countdown extends Interaction {
    static selector = ".s_countdown";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _wrapperEl: () =>
            this.el.querySelector(
                this.isV001 ? ".s_countdown_wrapper" : ".s_countdown_canvas_wrapper"
            ),
    };
    dynamicContent = {
        _wrapperEl: {
            "t-att-class": () => ({
                "d-flex": true,
                "justify-content-center": true,
            }),
        },
    };

    setup() {
        // Remove SVG previews (used to simulated canvas)
        this.el.querySelectorAll("svg").forEach((el) => el.parentNode.remove());

        // Before 001, the canvases were drawn in the wrapper itself; from 001
        // on, the circle layout has its own element inside of it.
        this.wrapperEl = this.el.querySelector(
            this.isV001 ? ".o_template_circle" : ".s_countdown_canvas_wrapper"
        );
        this.hereBeforeTimerEnds = false;
        this.endAction = this.el.dataset.endAction;
        this.endTime = parseInt(this.el.dataset.endTime);
        this.size = parseInt(this.el.dataset.size);
        this.display = this.el.dataset.display;

        this.defaultColor = "rgba(0, 0, 0, 0)";
        this.layout = this.el.dataset.layout;
        this.layoutBackground = this.el.dataset.layoutBackground;
        this.progressBarStyle = this.el.dataset.progressBarStyle;
        this.progressBarWeight = this.el.dataset.progressBarWeight;

        this.layoutBackgroundColor = this.ensureCSSColor(this.el.dataset.layoutBackgroundColor);
        this.progressBarColor = this.ensureCSSColor(this.el.dataset.progressBarColor);

        this.onlyOneUnit = this.display === "d";
        this.width = this.size;
        if (this.layout === "boxes") {
            this.width /= 1.75;
        }
        this.initTimeDiff();
        this.render();

        // Then keep rendering every second at 000 milliseconds, so that the
        // displayed values change at the same time as the actual ones.
        this.waitForTimeout(() => {
            this.render();
            this.setInterval = this.setSafeInterval(this.render, 1000);
        }, 1000 - (Date.now() % 1000));
    }

    destroy() {
        // The optional chaining is required because the queried element may not
        // exist anymore if the interaction target has just been deleted
        this.wrapperEl?.classList.remove("d-none");
        window.removeEventListener("resize", this.onResize);
    }

    /**
     * The markup changed with the version 001: both layouts now share the same
     * wrapper, and the values are part of the templates, so that they can be
     * edited.
     *
     * @returns {boolean}
     * @todo remove legacy code with version 23.0: vxml 001 was introduced with
     * 20.0, countdown snippets don't stay that long.
     * 
     */
    get isV001() {
        return this.el.dataset.vxml === "001";
    }

    get textColor() {
        // Before 001, the color was kept in a data attribute; it is now taken
        // from the element itself, so that it can be set with the text options.
        return this.ensureCSSColor(
            this.isV001 ? getComputedStyle(this.el).color : this.el.dataset.textColor
        );
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
            this.el.querySelector(".s_countdown_title")?.classList.add("d-none");
        }
        this.registerCleanup(() => {
            this.el.querySelector(".s_countdown_end_message")?.classList.add("d-none");
            this.el.querySelector(".s_countdown_title")?.classList.remove("d-none");
        });
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
        let canvas;
        if (this.isUnitVisible("d") && !(this.onlyOneUnit && delta < 86400)) {
            if (this.layout !== "text") {
                canvas = this.createCanvasWrapper();
                this.insert(canvas, this.wrapperEl);
            }
            this.timeDiff.push({
                canvas,
                // There is no logical number of unit (total) on which day units
                // can be compared against, so we use an arbitrary number.
                total: 15,
                label: _t("Days"),
                nbSeconds: 86400,
            });
        }
        if (this.isUnitVisible("h") || (this.onlyOneUnit && delta < 86400 && delta > 3600)) {
            if (this.layout !== "text") {
                canvas = this.createCanvasWrapper();
                this.insert(canvas, this.wrapperEl);
            }
            this.timeDiff.push({
                canvas,
                total: 24,
                label: _t("Hours"),
                nbSeconds: 3600,
            });
        }
        if (this.isUnitVisible("m") || (this.onlyOneUnit && delta < 3600 && delta > 60)) {
            if (this.layout !== "text") {
                canvas = this.createCanvasWrapper();
                this.insert(canvas, this.wrapperEl);
            }
            this.timeDiff.push({
                canvas,
                total: 60,
                label: _t("Minutes"),
                nbSeconds: 60,
            });
        }
        if (this.isUnitVisible("s") || (this.onlyOneUnit && delta < 60)) {
            if (this.layout !== "text") {
                canvas = this.createCanvasWrapper();
                this.insert(canvas, this.wrapperEl);
            }
            this.timeDiff.push({
                canvas,
                total: 60,
                label: _t("Seconds"),
                nbSeconds: 1,
            });
        }
        if (this.layout === "text" && !this.isV001) {
            // From 001 on, the label is already split in the markup.
            this.timeDiff.forEach((metric) => {
                if (metric.label) {
                    metric.label = this.wrapFirstLetter(metric.label);
                }
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
     * Toggles the visibility of the countdown, depending on the layout it uses
     * and on whether it should be hidden once finished.
     */
    updateWrappersVisibility() {
        if (this.isV001) {
            this.el
                .querySelector(".s_countdown_wrapper")
                .classList.toggle("d-none", this.shouldHideCountdown);
            return;
        }
        // Before 001, both layouts had their own wrapper in the markup.
        this.el
            .querySelector(".s_countdown_inline_wrapper")
            ?.classList.toggle("d-none", this.layout !== "text" || this.shouldHideCountdown);
        this.el
            .querySelector(".s_countdown_canvas_wrapper")
            ?.classList.toggle("d-none", this.layout === "text");
    }

    /**
     * Draws the whole countdown, including one countdown for each time unit.
     */
    render() {
        if (this.onlyOneUnit && this.getDelta() < this.timeDiff[0].nbSeconds) {
            this.el.querySelector(".s_countdown_canvas_flex")?.remove();
            this.initTimeDiff();
        }
        this.updateTimediff();

        this.updateWrappersVisibility();

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
                    const numberEls =
                        this.countItemNbsEls[index].querySelectorAll(".o_count_item_nb");
                    metric.nb.split("").forEach((number, i) => {
                        this.setValue(numberEls[i], number);
                    });
                } else {
                    this.setValue(this.countItemNbsEls[index], metric.nb);
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
     * Writes a value in an element, spread over the text nodes it is currently
     * split into: the user can have styled only a part of it (e.g. "23" as
     * `<span style="font-size: 20px">2</span>3`), and each piece has to keep
     * its own part of the new value.
     *
     * @param {Element} el
     * @param {string} value
     */
    setValue(el, value) {
        if (!el || !this.shouldUpdateValue(el)) {
            return;
        }
        if (!this.isV001) {
            // The values were not editable before 001.
            el.textContent = value;
            return;
        }
        const textNodes = this.getTextNodes(el);
        if (!textNodes.length) {
            el.append(value);
            return;
        }
        const lengths = textNodes.map((textNode) => textNode.length);
        const fitsSplit = lengths.reduce((total, length) => total + length, 0) === value.length;
        let index = 0;
        for (const [i, textNode] of textNodes.entries()) {
            let slice = value;
            if (fitsSplit) {
                slice = value.slice(index, index + lengths[i]);
            } else if (i > 0) {
                slice = "";
            }
            if (textNode.nodeValue !== slice) {
                textNode.nodeValue = slice;
            }
            index += lengths[i];
        }
    }

    /**
     * Hook allowing the edit mode to not update the element's value.
     *
     * @param {Element} el
     * @returns {boolean}
     */
    shouldUpdateValue(el) {
        return true;
    }

    getTextNodes(node) {
        return [...node.childNodes].flatMap((child) =>
            child.nodeType === Node.TEXT_NODE ? child : this.getTextNodes(child)
        );
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
