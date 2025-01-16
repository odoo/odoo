import { useBus, useService } from "@web/core/utils/hooks";
import { EventBus, Component, useEffect, useState } from "@odoo/owl";
import { redirect } from "@web/core/utils/urls";
import { delay } from "@web/core/utils/concurrency";

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

        this.state = useState({
            ...initialState,
        });
        this.getProgress;
        this.currentLoadingStepIndex;
        this.loaderInterval = null;
        this.loaderCloseStepDelay = 300;
        this.loaderCloseFinalDelay = 1500;

        useEffect(
            (isVisible) => {
                if (isVisible) {
                    // Prevent user from closing/refreshing the window while the
                    // loader is visible
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

            const instanceProps = ["getProgress"];
            for (const prop of instanceProps) {
                if (props && props[prop] !== undefined) {
                    this[prop] = props[prop];
                }
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
            await this.gracefulClose(completeRemainingProgress);

            for (const key of Object.keys(initialState)) {
                this.state[key] = initialState[key];
            }
        });
        // Action needed if the app automatically refreshes or redirects the
        // page without hiding/removing the WebsiteLoader. This should be
        // called if we want to refresh/redirect out of the website loader.
        useBus(this.props.bus, "REDIRECT-OUT-FROM-WEBSITE-LOADER", async (ev) => {
            const completeRemainingProgress = ev.detail?.completeRemainingProgress;
            const url = ev.detail?.url;

            await this.gracefulClose(completeRemainingProgress);
            window.removeEventListener("beforeunload", this.showRefreshConfirmation);

            if (url) {
                redirect(url);
            }
        });
    }

    /**
     * Starts the loader and begins periodically updating progress.
     * Chooses between mock or real progress depending on whether a
     * `getProgress` function is provided.
     *
     * @param {number} [progressUpdateInterval=500] - Interval in milliseconds
     *   between progress updates. Smaller values result in smoother progress
     *   animations but cause the progress update logic to run more often.
     */
    startLoader(progressUpdateInterval = 500) {
        if (this.loaderInterval) {
            return;
        }

        const isMockProgress = !this.getProgress || typeof this.getProgress !== "function";
        const totalSteps = this.state.loadingSteps.length;
        const progressPerStep = totalSteps ? 100 / totalSteps : 0;

        let mockCounter = 0;

        this.loaderInterval = setInterval(async () => {
            let newProgress;
            mockCounter += 0.05; // higher increment = mock progress completes faster

            if (isMockProgress) {
                newProgress = this.calculateMockProgress(mockCounter);
            } else {
                newProgress = await this.calculateRealProgress(
                    this.state.progressPercentage,
                    mockCounter
                );
            }

            this.state.progressPercentage = newProgress;
            this.updateLoadingSteps(newProgress, totalSteps, progressPerStep);
        }, progressUpdateInterval);
    }

    /**
     * Calculates the next progress value using a curved progression
     * (arctangent) to make the progress start fast and slow down as it
     * approaches completion.
     *
     * @param {number} counter - A steadily increasing counter used to compute
     *                           the mock progress percentage.
     * @returns {number} The next progress value.
     */
    calculateMockProgress(counter) {
        return Math.min((Math.atan(counter) / (Math.PI / 2)) * 100, 100);
    }

    /**
     * Calculates the next progress value using the provided `getProgress`
     * function.
     * Falls back to `calculateMockProgress` if `getProgress` fails or returns
     * an invalid value.
     *
     * @param {number} currentProgress - Current progress value.
     * @param {number} fallbackMockCounter - A steadily increasing counter used
     *   to compute the progress as a fallback if getting real progress fails.
     * @returns {Promise<number>} The next progress value.
     */
    async calculateRealProgress(currentProgress, fallbackMockCounter) {
        try {
            const result = await this.getProgress(currentProgress);
            if (typeof result === "number") {
                return Math.min(result, 100);
            } else {
                throw "Invalid progress value returned from 'getProgress' function";
            }
        } catch (err) {
            console.warn(
                "Progress update failed using getProgress function, using mock progress instead:",
                err
            );
            return this.calculateMockProgress(fallbackMockCounter);
        }
    }

    /**
     * Updates the current loading step based on `progressPercentage`.
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

            this.currentLoadingStepIndex = targetActiveStepIndex;
            this.state.currentLoadingStep = this.state.loadingSteps[targetActiveStepIndex];
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
     * Gracefully closes the loader by quickly completing any remaining steps
     * and updating the progress bar to 100%.
     *
     * @param {boolean} [completeRemainingProgress=true] - If true, shows
     *   remaining steps and completes progress bar quickly before closing. If
     *   false, closes the loader immediately.
     */
    async gracefulClose(completeRemainingProgress = true) {
        if (this.isClosing) {
            return;
        }

        this.isClosing = true;
        this.clearLoaderInterval();

        if (completeRemainingProgress) {
            const remainingStepsLength =
                this.state.loadingSteps.length - (this.currentLoadingStepIndex || 0);
            const remainingProgress = 100 - this.state.progressPercentage;
            const progressIncrement = remainingProgress / remainingStepsLength;

            if (remainingStepsLength === 0) {
                this.state.progressPercentage = 100;
            } else {
                // Quickly show all the remaining steps and complete the
                // progress bar
                for (
                    let index = this.currentLoadingStepIndex;
                    index < this.state.loadingSteps.length;
                    index++
                ) {
                    const step = this.state.loadingSteps[index];
                    this.state.currentLoadingStep = { ...step };
                    // Small delay to complete steps sequentially and not all at
                    // once.
                    await delay(this.loaderCloseStepDelay);

                    this.state.loadingSteps[index].completed = true;

                    this.state.progressPercentage = Math.min(
                        this.state.progressPercentage + progressIncrement,
                        100
                    );
                }
            }

            this.currentLoadingStepIndex = undefined;
            this.state.currentLoadingStep = undefined;

            // Wait for a moment to ensure the user sees that all the steps are
            // completed.
            await delay(this.loaderCloseFinalDelay);
        }

        this.isClosing = false;
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
