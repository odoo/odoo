import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";
import { Countdown } from "@website/snippets/s_countdown/countdown";

function circlePaint(color) {
    if (!color) {
        return "currentColor";
    }
    if (CSS.supports("color", color)) {
        return color;
    }
    return `var(--${color}, currentColor)`;
}

export class CountdownExperiment extends Countdown {
    static selector = ".s_countdown_experiment";

    createCanvasWrapper() {
        const { size, layoutBackground, progressBarStyle, progressBarWeight } = this;
        let strokeWidth = 10;
        let backgroundInset = layoutBackground === "plain" ? 0 : 10;
        if (progressBarWeight === "thin") {
            strokeWidth = 100 / 35;
            backgroundInset = layoutBackground === "plain" ? 100 / 29 : 100 / 15;
        }
        const backgroundRadius = 50 - backgroundInset;
        const unit = renderToElement("website.s_countdown_experiment.unit", {
            isCss: this.el.dataset.renderer === "css",
            hasBackground: layoutBackground !== "none",
            hasProgress: progressBarStyle !== "none",
            hasTrack: progressBarStyle === "surrounded",
            strokeWidth,
            backgroundRadius,
        });
        unit.style.setProperty("--countdown-experiment-size", `${size}px`);
        unit.style.setProperty("--countdown-experiment-ring-inner", `${90 - strokeWidth}%`);
        unit.style.setProperty("--countdown-experiment-ring-outer", `${90 + strokeWidth}%`);
        unit.style.setProperty(
            "--countdown-experiment-background-size",
            `${backgroundRadius * 2}%`
        );
        unit.style.setProperty(
            "--countdown-experiment-progress-color",
            circlePaint(this.el.dataset.progressBarColor)
        );
        unit.style.setProperty(
            "--countdown-experiment-background-color",
            circlePaint(this.el.dataset.layoutBackgroundColor)
        );
        return unit;
    }

    render() {
        const firstUnit = this.timeDiff[0];
        if (
            this.onlyOneUnit &&
            (!firstUnit || (firstUnit.nbSeconds > 1 && this.getDelta() < firstUnit.nbSeconds))
        ) {
            firstUnit?.canvas.remove();
            this.initTimeDiff();
        }
        this.updateTimediff();
        this.updateWrappersVisibility();

        if (!this.shouldHideCountdown) {
            for (const unit of this.timeDiff) {
                const progress = Math.max(0, Math.min(1, unit.nb / unit.total));
                unit.canvas.style.setProperty("--countdown-experiment-progress", progress);
                unit.canvas.querySelector(".o_countdown_experiment_number").textContent = unit.nb;
                unit.canvas.querySelector(".o_countdown_experiment_label").textContent = unit.label;
            }
        }
        if (this.isFinished) {
            clearInterval(this.setInterval);
            this.handleEndCountdownAction();
        }
    }
}

registry.category("public.interactions").add("website.countdown_experiment", CountdownExperiment);
