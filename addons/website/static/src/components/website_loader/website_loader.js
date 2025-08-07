import { rpc } from "@web/core/network/rpc";
import { useBus, useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";
import { EventBus, Component, markup, useEffect, useState } from "@odoo/owl";

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
            showTips: false,
            selectedFeatures: [],
            showWaitingMessages: false,
            progressPercentage: 0,
            bottomMessageTemplate: undefined,
            showLoader: true,
            showCloseButton: false,
        };

        const defaultMessages = [{
            title: _t("Building your website."),
            description: _t("Applying your colors and design..."),
            flag: "colors",
        }, {
            title: _t("Building your website."),
            description: _t("Searching your images...."),
            flag: "images",
        }, {
            title: _t("Building your website."),
            description: _t("Generating inspiring text..."),
            flag: "text",
        }];

        let messagesInterval;

        this.state = useState({
            ...initialState,
        });
        this.waitingMessages = useState(defaultMessages);
        this.currentWaitingMessage = useState({ ...defaultMessages[0] });
        this.featuresInstallInfo = { nbInstalled: 0, total: undefined };

        useEffect(
            (selectedFeatures) => {
                if (this.state.showWaitingMessages) {
                    let messagesToDisplay = [...defaultMessages]; // Start with defaultMessages
                    if (selectedFeatures.length > 0) {
                        // Merge defaultMessages with the relevant waitingMessages
                        messagesToDisplay.push(...this.getWaitingMessages(selectedFeatures));
                    }

                    this.waitingMessages.splice(0, this.waitingMessages.length, ...messagesToDisplay);

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

        // Cycle through the waitingMessages every 6s
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
                    }, 6000);

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
            for (const prop of [
                "title",
                // FIXME: website user/interactive tours are not properly
                // working at the moment. This disables the "follow the tips"
                // message in the website loader while waiting for a fix.
                // "showTips",
                "selectedFeatures",
                "showWaitingMessages",
                "bottomMessageTemplate",
                "showCloseButton",
                "flag",
            ]) {
                this.state[prop] = props && props[prop];
            }
            this.state.showLoader = props && props.showLoader !== false;
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
        const installInfo = await rpc(
            "/website/track_installing_modules",
            {
                'selected_features': selectedFeatures,
                'total_features': this.featuresInstallInfo.total,
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
    }

    /**
     * Depending on the features selected, returns the right waiting messages.
     *
     * @param {integer[]} selectedFeatures
     * @returns {Object[]} - the messages filtered by the selected features
     */
    getWaitingMessages(selectedFeatures) {
        const websiteFeaturesMessages = [{
            id: 5,
            title: _t("Adding features."),
            name: _t("blog"),
            description: _t("Enabling your %s."),
            flag: "generic",
        }, {
            id: 7,
            title: _t("Adding features."),
            name: _t("recruitment platform"),
            description: _t("Integrating your %s."),
            flag: "generic",
        }, {
            id: 8,
            title: _t("Adding features."),
            name: _t("online store"),
            description: _t("Activating your %s."),
            flag: "generic",
        }, {
            id: 9,
            title: _t("Adding features."),
            name: _t("online appointment system"),
            description: _t("Configuring your %s."),
            flag: "generic",
        }, {
            id: 10,
            title: _t("Adding features."),
            name: _t("forum"),
            description: _t("Setting up your %s."),
            flag: "generic",
        }, {
            id: 12,
            title: _t("Adding features."),
            name: _t("e-learning platform"),
            description: _t("Installing your %s."),
            flag: "generic",
        }, {
            // Always the last message if there is at least 1 feature selected.
            id: "last",
            title: _t("Finalizing."),
            description: _t("Activating the last features."),
            flag: "generic",
        }];

        const filteredIds = [...selectedFeatures, "last"];
        const messagesList = websiteFeaturesMessages.filter((msg) => {
            if (filteredIds.includes(msg.id)) {
                if (msg.name) {
                    const highlight = sprintf(
                        '<span class="o_website_loader_text_highlight">%s</span>', msg.name
                    );
                    msg.description = markup(sprintf(msg.description, highlight));
                }
                return true;
            }
        });
        return messagesList;
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
