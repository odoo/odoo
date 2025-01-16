import { Component, EventBus, useEffect, useState } from "@odoo/owl";
import { delay } from "@web/core/utils/concurrency";
import { useBus, useService } from "@web/core/utils/hooks";
import { clamp } from "@web/core/utils/numbers";

export class WebsiteLoader extends Component {
    static props = {
        bus: EventBus,
    };
    static template = "website.website_loader";

    setup() {
        this.website = useService("website");

        const initialState = {
            isVisible: false,
            title: "Enhance your site in seconds.",
            flag: "generic",
            loadingSteps: [],
            currentLoadingStep: undefined,
            progressPercentage: 0,
            bottomMessageTemplate: undefined,
            showProgressBar: true,
            showCloseButton: false,
        };
        const initialInstanceState = {
            getProgress: null,
            currentLoadingStepIndex: null,
            loaderInterval: null,
        };

        this.state = useState({
            ...initialState,
        });
        Object.assign(this, initialInstanceState);
        this.stopProgressStepDelay = 300;
        this.stopProgressFinalPause = 1500;

        useEffect(
            (isVisible) => {
                if (isVisible) {
                    // Prevent user from closing/refreshing the window while the
                    // loader is visible.
                    window.addEventListener("beforeunload", this.showRefreshConfirmation);
                    this.startLoader();
                } else {
                    window.removeEventListener("beforeunload", this.showRefreshConfirmation);
                }

                return () => {
                    window.removeEventListener("beforeunload", this.showRefreshConfirmation);
                    this.clearLoaderInterval();
                };
            },
            () => [this.state.isVisible]
        );

        useBus(this.props.bus, "SHOW-WEBSITE-LOADER", (ev) => {
            const props = ev.detail;
            this.state.isVisible = true;
            for (const prop of [
                "title",
                "bottomMessageTemplate",
                "loadingSteps",
                "showCloseButton",
                "showProgressBar",
                "flag",
            ]) {
                if (props && props[prop] !== undefined) {
                    this.state[prop] = props[prop];
                }
            }

            if (props?.getProgress) {
                this.getProgress = props.getProgress;
            }

            if (props?.loadingSteps?.length) {
                this.currentLoadingStepIndex = 0;
                this.state.currentLoadingStep = { ...props.loadingSteps[0] };
            } else {
                this.currentLoadingStepIndex = undefined;
                this.state.currentLoadingStep = undefined;
            }
        });
        useBus(this.props.bus, "HIDE-WEBSITE-LOADER", async (ev) => {
            if (!this.state.isVisible) {
                return;
            }

            const completeRemainingProgress = ev.detail?.completeRemainingProgress;
            await this.stopProgress(completeRemainingProgress);

            for (const key of Object.keys(initialState)) {
                this.state[key] = initialState[key];
            }
            Object.assign(this, initialInstanceState);
        });
        // Action needed if the app automatically refreshes or redirects the
        // page without hiding/removing the WebsiteLoader. This should be
        // called to refresh/redirect if the loader is still visible.
        useBus(this.props.bus, "REDIRECT-OUT-FROM-WEBSITE-LOADER", async (ev) => {
            const completeRemainingProgress = ev.detail?.completeRemainingProgress;
            const redirectAction = ev.detail?.redirectAction;

            await this.stopProgress(completeRemainingProgress);
            window.removeEventListener("beforeunload", this.showRefreshConfirmation);

            await redirectAction?.();
        });
    }

    /**
     * Starts the loader and begins periodically updating progress.
     * Chooses between internally simulated progress or externally driven
     * progress depending on whether a `getProgress` function is provided.
     *
     * @param {number} [progressUpdateInterval=500] - Interval in milliseconds
     *   between progress updates. Smaller values result in smoother progress
     *   animations but cause the progress update logic to run more often.
     */
    startLoader(progressUpdateInterval = 500) {
        if (this.loaderInterval) {
            return;
        }

        const isInternalProgress = typeof this.getProgress !== "function";
        const totalSteps = this.state.loadingSteps.length;
        const progressPerStep = totalSteps ? 100 / totalSteps : 0;

        let isUpdating = false;
        let internalCounter = 0;

        this.loaderInterval = setInterval(async () => {
            if (isUpdating) {
                return;
            }

            isUpdating = true;
            internalCounter += 0.05; // higher increment = internal progress completes faster

            let newProgress;
            if (isInternalProgress) {
                newProgress = this.calculateInternalProgress(internalCounter);
            } else {
                newProgress = await this.calculateExternalProgress(
                    this.state.progressPercentage,
                    internalCounter
                );
            }

            this.state.progressPercentage = newProgress;
            this.updateLoadingSteps(newProgress, totalSteps, progressPerStep);

            isUpdating = false;
        }, progressUpdateInterval);
    }

    /**
     * Calculates the next progress value using a curved progression
     * (arctangent) to make the progress start fast and slow down as it
     * approaches completion.
     *
     * @param {number} counter - A steadily increasing counter used to compute
     *                           the internal progress percentage.
     * @returns {number} The next progress value.
     */
    calculateInternalProgress(counter) {
        const normalized = Math.atan(counter) / (Math.PI / 2);
        return Math.min(normalized * 100, 100);
    }

    /**
     * Calculates the next progress value using the `getProgress` function.
     * Falls back to `calculateInternalProgress` if `getProgress` fails or
     * returns an invalid value.
     *
     * @param {number} currentProgress - Current progress value.
     * @param {number} fallbackInternalCounter - A steadily increasing counter
     *   used to compute the progress as a fallback if getting real progress
     *   fails.
     * @returns {Promise<number>} The next progress value.
     */
    async calculateExternalProgress(currentProgress, fallbackInternalCounter) {
        try {
            const result = await this.getProgress(currentProgress);
            if (typeof result !== "number" || isNaN(result)) {
                throw new Error(`Invalid progress value: ${result}`);
            }
            return clamp(result, 0, 100);
        } catch (err) {
            console.warn("getProgress failed, falling back to internal progress:", err);
            return Math.max(
                this.calculateInternalProgress(fallbackInternalCounter),
                currentProgress
            );
        }
    }

    /**
     * Updates the current loading step based on `progressPercentage`.
     *
     * @param {number} currentProgress - The current progress value (0-100).
     * @param {number} totalSteps - Total number of loading steps.
     * @param {number} progressPerStep - Progress percentage allocated per step.
     */
    updateLoadingSteps(currentProgress, totalSteps, progressPerStep) {
        if (!totalSteps) {
            return;
        }

        const targetActiveStepIndex = Math.min(
            Math.floor(currentProgress / progressPerStep),
            totalSteps - 1
        );

        if (this.currentLoadingStepIndex !== targetActiveStepIndex) {
            // Mark all previous loading steps as completed (again).
            // This ensures that if the progress jumps significantly, no
            // intermediate loading steps remain incomplete.
            for (let index = 0; index < targetActiveStepIndex; index++) {
                this.state.loadingSteps[index].completed = true;
            }

            const targetStep = this.state.loadingSteps[targetActiveStepIndex];
            if (targetStep) {
                this.currentLoadingStepIndex = targetActiveStepIndex;
                this.state.currentLoadingStep = targetStep;
            }
        }
    }

    /**
     * Cleans up the loader interval.
     */
    clearLoaderInterval() {
        if (this.loaderInterval) {
            clearInterval(this.loaderInterval);
            this.loaderInterval = null;
        }
    }

    /**
     * Stops the loader progress and optionally completes any remaining steps
     * gracefully, updating the progress bar to 100%.
     *
     * @param {boolean} [completeRemainingProgress=true] - If true, completes
     *   any remaining steps before stopping. If false, stops immediately.
     */
    async stopProgress(completeRemainingProgress = true) {
        this.clearLoaderInterval();

        if (!completeRemainingProgress) {
            return;
        }

        const startIndex = this.currentLoadingStepIndex ?? 0;
        const remainingStepsLength = this.state.loadingSteps.length - startIndex;

        if (remainingStepsLength <= 0) {
            this.state.progressPercentage = 100;
        } else {
            const remainingProgress = 100 - this.state.progressPercentage;
            const progressIncrement = remainingProgress / remainingStepsLength;

            for (let index = startIndex; index < this.state.loadingSteps.length; index++) {
                const step = this.state.loadingSteps[index];
                this.state.currentLoadingStep = { ...step };

                // Small delay to complete steps sequentially and not all at
                // once.
                await delay(this.stopProgressStepDelay);

                this.state.loadingSteps[index].completed = true;
                this.state.progressPercentage = Math.min(
                    this.state.progressPercentage + progressIncrement,
                    100
                );
            }
        }

        this.currentLoadingStepIndex = undefined;
        this.state.currentLoadingStep = undefined;

        // Pause for a moment to ensure the user sees that all the steps are
        // completed.
        await delay(this.stopProgressFinalPause);
    }

    /**
     * Prevents refreshing/leaving the page if the loader is displayed (and
     * thus some work is being done in the backend) by opening a prompt dialog.
     *
     * @param {Event} ev
     * @returns empty returnValue for Chrome & Safari
     * cf. https://developer.mozilla.org/en-US/docs/Web/API/Window/beforeunload_event#compatibility_notes
     */
    showRefreshConfirmation = (ev) => {
        if (this.state.isVisible) {
            ev.preventDefault(); // Firefox
            ev.returnValue = "";
            return ev.returnValue;
        }
    };

    /**
     * Hide the loader.
     */
    close() {
        this.website.hideLoader();
    }
}
