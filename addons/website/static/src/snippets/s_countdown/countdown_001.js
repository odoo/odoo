import { registry } from "@web/core/registry";
import { Countdown } from "./countdown";

export class Countdown001 extends Countdown {
    static selector = ".s_countdown[data-vxml='001']";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _wrapperEl: () => this.el.querySelector(".s_countdown_wrapper"),
    };

    setup() {
        super.setup();
    }

    getCircleWrapperEl() {
        return this.el.querySelector(".o_template_circle");
    }

    /**
     * Returns color of the countdown text
     *
     * @returns {string}
     */
    get textColor() {
        return this.ensureCSSColor(getComputedStyle(this.el).color);
    }

    /**
     * Overrides the original method. Needed because we use the metric label
     * string directly in `render()`.
     */
    wrapFirstLetter(string) {
        return string;
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

        // We toggle the wrapper visibility if the countdown is finished.
        this.el
            .querySelector(".s_countdown_wrapper")
            .classList.toggle("d-none", this.shouldHideCountdown);

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
                        // Numbers can be wrapped inside of some elements(font, span, etc)
                        // if a user modified it before. To preserve the style we should get
                        // the deepest node
                        const countItemNbEl = this.getDeepestChild(
                            this.countItemNbsEls[index].querySelectorAll("span")[i]
                        );
                        countItemNbEl.textContent = number;
                    });
                } else {
                    const countItemNbsEl = this.getDeepestChild(this.countItemNbsEls[index]);
                    countItemNbsEl.textContent = String(metric.nb).padStart(2, "0");
                }
                const labelEl = this.countItemLabelEls[index];
                const firstLetterEl = this.getDeepestChild(
                    labelEl.querySelector(".o_first_letter")
                );
                const otherLettersEl = this.getDeepestChild(
                    labelEl.querySelector(".o_other_letters")
                );
                if (firstLetterEl && otherLettersEl) {
                    firstLetterEl.textContent = metric.label[0];
                    otherLettersEl.textContent = metric.label.slice(1);
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
     * Returns the deepest descendant by following firstElementChild.
     * At each level of traversal, all sibling nodes (including text nodes)
     * of the next firstElementChild are removed, so the returned element
     * is the remaining child at every level of the chain.
     *
     * @param {Element} node - Starting element.
     * @returns {Element} The last element in the firstElementChild chain,
     * or the same node if it has no element children.
     */
    getDeepestChild(node) {
        while (node.firstElementChild) {
            [...node.childNodes].forEach((child) => {
                if (child !== node.firstElementChild) {
                    child.remove();
                }
            });
            node = node.firstElementChild;
        }
        return node;
    }
}

registry.category("public.interactions").add("website.countdown_001", Countdown001);
