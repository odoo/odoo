import { useDynamicInterval } from "@mail/utils/common/misc";
import { Component, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

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
            selectedOptionIds: new Set(),
            voting: false,
        });
        useDynamicInterval(
            (endDt) => {
                if (!endDt) {
                    return;
                }
                const diff = endDt.diffNow(["hours", "minutes", "seconds"]);
                if (diff.valueOf() <= 0) {
                    this.state.remainingTimeText = _t("Poll will end soon");
                    return;
                }
                const hours = Math.ceil(diff.as("hours"));
                if (hours > 1) {
                    this.state.remainingTimeText = _t("%(hours)s hours left", { hours });
                    return (diff.as("hours") - hours + 1) * 3600 * 1000;
                }
                const minutes = Math.ceil(diff.as("minutes"));
                if (minutes > 1) {
                    this.state.remainingTimeText = _t("%(minutes)s minutes left", { minutes });
                    return (diff.as("minutes") - minutes + 1) * 60 * 1000;
                }
                const seconds = Math.ceil(diff.as("seconds"));
                this.state.remainingTimeText =
                    seconds > 1 ? _t("%(seconds)s seconds left", { seconds }) : _t("1 second left");
                return (diff.as("seconds") - seconds + 1) * 1000;
            },
            () => [this.props.poll.poll_end_dt]
        );
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
