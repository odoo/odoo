import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @property {import("models").Poll} poll
 * @extends {Component<Props, Env>}
 */
export class Poll extends Component {
    static template = "mail.Poll";
    static props = ["poll"];

    setup() {
        this.state = useState({
            remainingTimeText: "",
            showResults: false,
            selectedOptionIds: new Set(),
            voting: false,
        });
        let remainingTimeTimeout;
        const updateRemainingTime = () => {
            const diff = this.props.poll.endDateTime.diffNow(["hours", "minutes", "seconds"]);
            let remainingTimeText;
            if (diff.valueOf() <= 0) {
                this.state.remainingTimeText = _t("Poll will end soon");
                clearTimeout(remainingTimeTimeout);
                return;
            }
            const hours = Math.ceil(diff.as("hours"));
            const minutes = Math.ceil(diff.as("minutes"));
            const seconds = Math.ceil(diff.as("seconds"));
            if (hours > 1) {
                remainingTimeText = _t("%(hours)s hours left", { hours });
            } else if (minutes > 1) {
                remainingTimeText = _t("%(minutes)s minutes left", { minutes });
            } else {
                if (seconds === 1) {
                    remainingTimeText = _t("1 second left");
                } else {
                    remainingTimeText = _t("%(seconds)s seconds left", { seconds });
                }
            }
            this.state.remainingTimeText = remainingTimeText;
            const nextCallDelay = minutes > 1 ? 60_000 : 1000;
            remainingTimeTimeout = setTimeout(updateRemainingTime, nextCallDelay);
        };
        onMounted(() => {
            updateRemainingTime();
        });
        onWillUnmount(() => clearTimeout(remainingTimeTimeout));
    }

    toggleShowResults() {
        this.state.showResults = !this.state.showResults;
    }

    get showResults() {
        return (
            this.props.poll.selfAlreadyVoted ||
            this.props.poll.end_message_id ||
            this.state.showResults
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
        return this.showResults ? `background-size: ${option.vote_percentage}%;` : "";
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
