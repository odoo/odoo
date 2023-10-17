/** @odoo-module **/

import { useBus, useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";
import { EventBus, Component, markup, useEffect, useState } from "@odoo/owl";

export class WebsiteLoader extends Component {
    setup() {
        this.rpc = useService("rpc");

        const initialState = {
            isVisible: false,
            title: '',
            showTips: false,
            selectedFeatures: [],
            showWaitingMessages: false,
            progressPercentage: 0,
        };
        const defaultMessage = {
            title: _t("Building your website."),
            description: _t("Stay tuned for an exciting new online presence."),
        };
        let messagesInterval;

        this.state = useState({
            ...initialState,
        });
        this.waitingMessages = useState([ defaultMessage ]);
        this.currentWaitingMessage = useState({ ...defaultMessage });
        this.featuresInstallInfo = { nbInstalled: 0, total: undefined };

        useEffect(
            (selectedFeatures) => {
                if (this.state.showWaitingMessages && selectedFeatures.length > 0) {
                    // Populate this.waitingMessages with the relevant ones
                    this.waitingMessages.splice(1, this.waitingMessages.length,
                        ...this.getWaitingMessages(selectedFeatures));

                    // Request the number of modules/dependencies to install
                    // and already installed
                    this.trackModules(selectedFeatures).catch(console.error);

                    return () => {
                        clearTimeout(this.trackModulesTimeout);
                        clearInterval(this.updateProgressInterval);
                    };
                }
            },
            () => [this.state.selectedFeatures]
        );

        // Cycle through the waitingMessages every 10s
        useEffect(
            () => {
                if (this.state.showWaitingMessages) {
                    let msgIndex = 0;
                    messagesInterval = setInterval(() => {
                        msgIndex++;
                        const nextMessage = this.waitingMessages[msgIndex];
                        Object.assign(this.currentWaitingMessage, nextMessage);
                        if (this.waitingMessages.length - 1 === msgIndex) {
                            clearInterval(messagesInterval);
                        }
                    }, 10000);

                    return () => clearInterval(messagesInterval);
                }
            },
            () => [this.waitingMessages.length]
        );

        // Prevent user from closing/refreshing the window
        useEffect(
            (isVisible) => {
                if (isVisible) {
                    window.addEventListener("beforeunload", this.showRefreshConfirmation);
                    if (!this.state.selectedFeatures || this.state.selectedFeatures.length === 0) {
                        // If there is no feature selected, we fake the progress
                        // for theme installation and configurator_apply. If
                        // there is at least 1 feature selected, the progress
                        // bar will be initialized in trackModules().
                        this.initProgressBar();
                    }
                } else {
                    window.removeEventListener("beforeunload", this.showRefreshConfirmation);
                }

                return () => {
                    window.removeEventListener("beforeunload", this.showRefreshConfirmation);
                    clearInterval(this.updateProgressInterval);
                };
            },
            () => [this.state.isVisible]
        );

        useBus(this.props.bus, "SHOW-WEBSITE-LOADER", (ev) => {
            const props = ev.detail;
            this.state.isVisible = true;
            this.state.title = props && props.title;
            this.state.showTips = props && props.showTips;
            this.state.selectedFeatures = props && props.selectedFeatures;
            this.state.showWaitingMessages = props && props.showWaitingMessages;
        });
        useBus(this.props.bus, "HIDE-WEBSITE-LOADER", () => {
            for (const key of Object.keys(initialState)) {
                this.state[key] = initialState[key];
            }
            clearInterval(messagesInterval);
            clearTimeout(this.trackModulesTimeout);
            clearInterval(this.updateProgressInterval);
        });
        // Action needed if the app automatically refreshes or redirects the
        // page without hiding/removing the WebsiteLoader. This should be
        // called prior to any refresh/redirect if the loader is still visible.
        useBus(this.props.bus, "PREPARE-OUT-WEBSITE-LOADER", () => {
            window.removeEventListener("beforeunload", this.showRefreshConfirmation);
        });
    }

    /**
     * Initializes the progress bar.
     */
    initProgressBar() {
        if (this.updateProgressInterval) {
            return;
        }
        // The progress speed decreases as it approaches its limit. This way,
        // users have the feeling that the website creation progressing is fast
        // and we prevent them from leaving the page too early (because they
        // already did XX% of the process).
        // If there is no module to install, we fake the progress from 0 to 100.
        // If there is at least 1 module to install, we take 70% of the progress
        // bar that we divide by the number of modules to install. We fake the
        // progress of each module individually and when all modules are
        // installed, we fake the progress of the remaining 30%.
        const nbModulesToInstall = this.featuresInstallInfo.total || 0;
        const isSomethingToInstall = nbModulesToInstall > 0;
        let currentProgress = 0;
        // This controls the speed of the progress bar.
        const progressStep = isSomethingToInstall ? 0.04 : 0.02;
        let progressForAfterModules = isSomethingToInstall ? 30 : 100;
        let progressForAllModules = 100 - progressForAfterModules;
        let lastTotalInstalled = 0;
        let progressPerModule = isSomethingToInstall ?
            progressForAllModules / nbModulesToInstall : 0;

        this.updateProgressInterval = setInterval(() => {
            if (this.featuresInstallInfo.nbInstalled !== lastTotalInstalled) {
                // A module just finished its install.
                currentProgress = 0;
                lastTotalInstalled = this.featuresInstallInfo.nbInstalled;
            }
            currentProgress += progressStep;
            const limit = this.featuresInstallInfo.nbInstalled === nbModulesToInstall ?
                progressForAfterModules : progressPerModule;
            this.state.progressPercentage = (lastTotalInstalled * progressPerModule) +
                Math.atan(currentProgress) / (Math.PI / 2) * limit;
        }, 100);
    }
    /**
     * Makes a RPC call to track the features and dependencies being installed
     * and, as long as the number of features installed is different from the
     * total expected, recursively calls itself again after 1s.
     *
     * @param {integer[]} selectedFeatures
     */
    async trackModules(selectedFeatures) {
        const installInfo = await this.rpc(
            "/website/track_installing_modules",
            {
                selected_features: selectedFeatures,
                total_features: this.featuresInstallInfo.total,
            },
            { silent: true }
        );
        if (!this.featuresInstallInfo.total
            || this.featuresInstallInfo.nbInstalled !== installInfo.nbInstalled) {
            this.featuresInstallInfo = installInfo;
        }
        this.initProgressBar();
        if (this.featuresInstallInfo.nbInstalled !== this.featuresInstallInfo.total) {
            this.trackModulesTimeout = setTimeout(() => this.trackModules(selectedFeatures), 1000);
        }
    };

    /**
     * Depending on the features selected, returns the right waiting messages.
     *
     * @param {integer[]} selectedFeatures
     * @returns {Object[]} - the messages filtered by the selected features
     */
    getWaitingMessages(selectedFeatures) {
        const websiteFeaturesMessages = [{
            id: 5,
            title: _t("Enabling your %s."),
            name: _t("blog"),
            description: _t("Share your thoughts and ideas with the world."),
        }, {
            id: 7,
            title: _t("Integrating your %s."),
            name: _t("recruitment platform"),
            description: _t("Find the best talent for your team."),
        }, {
            id: 8,
            title: _t("Activating your %s."),
            name: _t("online store"),
            description: _t("Start selling your products and services today."),
        }, {
            id: 9,
            title: _t("Configuring your %s."),
            name: _t("online appointment system"),
            description: _t("Make it easy for clients to book appointments with you."),
        }, {
            id: 10,
            title: _t("Setting up your %s."),
            name: _t("forum"),
            description: _t("Engage with your community and build relationships."),
        }, {
            id: 12,
            title: _t("Installing your %s."),
            name: _t("e-learning platform"),
            description: _t("Offer online courses and learning opportunities."),
        }, {
            // Always the last message if there is at least 1 feature selected.
            id: "last",
            title: _t("Activating the last features."),
            description: _t("A bit more patience as your website takes shape."),
        }];

        const filteredIds = [...selectedFeatures, "last"];
        const messagesList = websiteFeaturesMessages.filter((msg) => {
            if (filteredIds.includes(msg.id)) {
                if (msg.name) {
                    const highlight = sprintf(
                        '<span class="o_website_loader_text_highlight">%s</span>', msg.name
                    );
                    msg.title = markup(sprintf(msg.title, highlight));
                }
                return true;
            }
        });
        return messagesList;
    };

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
}
WebsiteLoader.props = {
    bus: EventBus,
};
WebsiteLoader.template = 'website.website_loader';
