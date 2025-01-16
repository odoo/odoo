import { useBus, useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { EventBus, Component, useEffect, useState } from "@odoo/owl";
import { redirect } from "@web/core/utils/urls";

export class WebsiteLoader extends Component {
    static props = {
        bus: EventBus,
    };
    static template = "website.website_loader";

    setup() {
        this.website = useService("website");

        const initialState = {
            isVisible: false,
            title: '',
            flag: false,
            showLoadingMessages: true,
            progressPercentage: 0,
            bottomMessageTemplate: undefined,
            showProgressBar: true,
            showCloseButton: false,
            loadingMessages: [
                {
                    title: _t("Enhance your site in seconds."),
                    flag: "generic",
                },
            ],
            getProgress: undefined,
        };

        this.state = useState({
            ...initialState,
        });

        this.loaderInterval = null;
        this.loaderIntervalDelay = 500;
        this.waitingMessages = useState(this.state.loadingMessages);
        this.currentWaitingMessageIndex = 0;
        this.currentWaitingMessage = useState({ ...this.state.loadingMessages[0] });

        useEffect(
            (isVisible) => {
                if (isVisible) {
                    // Prevent user from closing/refreshing the window while the
                    // loader is visible
                    window.addEventListener("beforeunload", this.showRefreshConfirmation);
                    this.initLoader();
                } else {
                    window.removeEventListener("beforeunload", this.showRefreshConfirmation);
                }

                return () => {
                    window.removeEventListener("beforeunload", this.showRefreshConfirmation);
                    this.clearLoader();
                };
            },
            () => [this.state.isVisible]
        );

        useBus(this.props.bus, "SHOW-WEBSITE-LOADER", (ev) => {
            const props = ev.detail;
            this.state.isVisible = true;

            for (const prop of [
                "title",
                "showLoadingMessages",
                "bottomMessageTemplate",
                "showCloseButton",
                "flag",
                "loadingMessages",
                "getProgress",
            ]) {
                if (props && props[prop] !== undefined) {
                    this.state[prop] = props[prop];
                }
            }

            this.state.showProgressBar = props && props.showProgressBar !== false;

            // Update or reset the waiting messages
            this.currentWaitingMessageIndex = 0;
            if (props?.loadingMessages?.length) {
                this.currentWaitingMessage = { ...props.loadingMessages[0] };
                this.waitingMessages = [...props.loadingMessages];
            } else {
                this.currentWaitingMessage = undefined;
                this.waitingMessages = [];
            }
        });
        useBus(this.props.bus, "HIDE-WEBSITE-LOADER", async (ev) => {
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
            await this.gracefulClose(completeRemainingProgress);

            window.removeEventListener("beforeunload", this.showRefreshConfirmation);

            const url = ev.detail?.url;
            if (url) {
                redirect(url);
            }
        });
    }

    /**
     * Handles the loader initialization and progress updates
     */
    initLoader() {
        if (this.loaderInterval) {
            return;
        }

        let currentProgress = 0;
        const isMockProgress =
            !this.state.getProgress || typeof this.state.getProgress !== "function";

        this.loaderInterval = setInterval(async () => {
            if (isMockProgress) {
                currentProgress = this.updateMockProgress(currentProgress);
            } else {
                currentProgress = await this.updateRealProgress(currentProgress);
            }

            this.updateWaitingMessage();
        }, this.loaderIntervalDelay);
    }

    /**
     * Updates progress for mock loading (when getProgress function is not
     * provided).
     *
     * @param {number} currentProgress
     * @returns {number} Updated progress value
     */
    updateMockProgress(currentProgress) {
        const increment = 0.05;
        currentProgress += increment;
        this.state.progressPercentage = Math.min(
            (Math.atan(currentProgress) / (Math.PI / 2)) * 100,
            100
        );
        return currentProgress;
    }

    /**
     * Updates progress using the provided getProgress function.
     *
     * @param {number} currentProgress
     * @returns {number} Updated progress value
     */
    async updateRealProgress(currentProgress) {
        try {
            const result = await this.state.getProgress();
            if (result && typeof result === "number") {
                this.state.progressPercentage = Math.min(result, 100);
                return currentProgress;
            } else {
                throw new Error("Invalid progress value returned from getProgress function");
            }
        } catch (err) {
            console.error("Error in getProgress function: ", err);
            return this.updateMockProgress(currentProgress);
        }
    }

    /**
     * Updates the current waiting message based on progress.
     */
    updateWaitingMessage() {
        if (this.waitingMessages.length === 0) {
            return;
        }

        const totalMessages = this.waitingMessages.length;
        const progressPerMessage = 100 / totalMessages;
        const progressBasedMessageIndex = Math.min(
            Math.floor(this.state.progressPercentage / progressPerMessage),
            totalMessages - 1
        );

        if (this.currentWaitingMessageIndex !== progressBasedMessageIndex) {
            // Mark all previous waiting messages as completed.
            // This ensures that if the progress jumps significantly, any
            // intermediate waiting messages are not left marked as incomplete.
            for (let i = 0; i < progressBasedMessageIndex; i++) {
                this.waitingMessages[i].completed = true;
            }

            this.currentWaitingMessageIndex = progressBasedMessageIndex;
            this.currentWaitingMessage = this.waitingMessages[this.currentWaitingMessageIndex];
        }
    }

    /**
     * Cleans up the loader interval.
     */
    clearLoader() {
        if (this.loaderInterval) {
            clearInterval(this.loaderInterval);
            this.loaderInterval = null;
        }
    }

    /**
     * Gracefully closes the loader by quickly completing any remaining messages
     * and updating the progress bar to 100%.
     *
     * @param {boolean} completeRemainingProgress - If true, shows remaining
     * messages and completes progress bar. If false, closes the loader
     * immediately
     */
    async gracefulClose(completeRemainingProgress = true) {
        if (this.state.isClosing) {
            return;
        }

        this.state.isClosing = true;
        this.clearLoader();

        if (completeRemainingProgress) {
            const remainingMessagesLength =
                this.waitingMessages.length - this.currentWaitingMessageIndex;
            const remainingProgress = 100 - this.state.progressPercentage;
            const progressIncrement = remainingProgress / remainingMessagesLength;

            if (remainingMessagesLength === 0) {
                this.state.progressPercentage = 100;
            } else {
                // Quickly show all the remaining messages and complete the
                // progress bar
                for (
                    let i = this.currentWaitingMessageIndex;
                    i < this.waitingMessages.length;
                    i++
                ) {
                    const message = this.waitingMessages[i];
                    this.currentWaitingMessage = { ...message };
                    await new Promise((resolve) => setTimeout(resolve, 600));

                    this.waitingMessages[i].completed = true;

                    this.state.progressPercentage = Math.min(
                        this.state.progressPercentage + progressIncrement,
                        100
                    );
                }
            }

            // Wait for a moment to ensure the user sees that all the messages
            // are completed.
            await new Promise((resolve) => setTimeout(resolve, 1500));
        }

        this.state.isClosing = false;
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
