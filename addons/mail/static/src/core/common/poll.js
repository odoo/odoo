import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

/**
 * @typedef {Object} Props
 * @property {import("models").MailPollModel} poll
 * @extends {Component<Props, Env>}
 */
export class Poll extends Component {
    static template = "mail.Poll";
    static props = ["poll"];

    setup() {
        this.state = useState({
            isShowingResults: false,
            remainingTimeText: "",
            selectedOptionIds: new Set(),
            voting: false,
        });
        let remainingTimeTimeout;
        const updateRemainingTime = () => {
            this.state.remainingTimeText = this.props.poll.remainingTimeText;
            if (this.props.poll.poll_end_dt < DateTime.now()) {
                return;
            }
            remainingTimeTimeout = setTimeout(() => updateRemainingTime(), 1000);
        };
        onMounted(() => {
            updateRemainingTime();
        });
        onWillUnmount(() => clearTimeout(remainingTimeTimeout));
    }

    showResults() {
        this.state.isShowingResults = true;
    }

    hideResults() {
        this.state.isShowingResults = false;
    }

    get isShowingResults() {
        return (
            this.props.poll.selfAlreadyVoted ||
            this.props.poll.end_message_id ||
            this.state.isShowingResults
        );
    }

    async onClickVote() {
        if (this.state.voting) {
            return;
        }
        try {
            this.state.voting = true;
            await this.props.poll.vote([...this.state.selectedOptionIds]);
        } finally {
            this.state.voting = false;
            this.state.selectedOptionIds.clear();
        }
    }

    onOptionCheckboxToggle(optionId, checked) {
        if (!this.props.poll.allow_multiple_options) {
            this.state.selectedOptionIds.clear();
        }
        if (checked) {
            this.state.selectedOptionIds.add(optionId);
        } else {
            this.state.selectedOptionIds.delete(optionId);
        }
    }

    get voteButtonDisabled() {
        return this.state.selectedOptionIds.size === 0 || this.state.voting;
    }

    percentageAttStyle(option) {
        return this.isShowingResults ? `background-size: ${option.vote_percentage}%;` : "";
    }

    voteCountText(numberOfVotes) {
        switch (numberOfVotes) {
            case 0:
                return _t("0 votes");
            case 1:
                return _t("1 vote");
            default:
                return _t("%(count)s votes", { count: numberOfVotes });
        }
    }
}
