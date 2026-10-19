import { PollVotesPanel } from "@mail/core/common/poll_votes_panel";
import { computedUntilStale } from "@mail/utils/common/signal";

import { Component, proxy, signal, types, useProps } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

export class Poll extends Component {
    static template = "mail.Poll";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = useProps({
            poll: types.instanceOf(this.store["mail.poll"]),
        });
        /** @type {import("@odoo/owl").Signal<Element>} */
        this.rootRef = signal();
        this.state = proxy({
            isShowingResults: false,
            selectedOptionIds: new Set(),
            voting: false,
        });
        this.remainingTime = computedUntilStale(
            () => {
                const endDt = this.props.poll.poll_end_dt;
                if (!endDt) {
                    return { text: "" };
                }
                const diff = endDt.diffNow(["hours", "minutes", "seconds"]);
                if (diff.valueOf() <= 0) {
                    return { text: _t("Poll will end soon") };
                }
                const hours = Math.ceil(diff.as("hours"));
                if (hours > 1) {
                    return {
                        text: _t("%(hours)s hours left", { hours }),
                        ms: (diff.as("hours") - hours + 1) * 3600 * 1000,
                    };
                }
                const minutes = Math.ceil(diff.as("minutes"));
                if (minutes > 1) {
                    return {
                        text: _t("%(minutes)s minutes left", { minutes }),
                        ms: (diff.as("minutes") - minutes + 1) * 60 * 1000,
                    };
                }
                const seconds = Math.ceil(diff.as("seconds"));
                return {
                    text:
                        seconds > 1
                            ? _t("%(seconds)s seconds left", { seconds })
                            : _t("1 second left"),
                    ms: (diff.as("seconds") - seconds + 1) * 1000,
                };
            },
            ({ ms }) => ms
        );
    }

    get remainingTimeTextTitle() {
        if (!this.props.poll.poll_end_dt) {
            return "";
        }
        return _t("Poll ends on %(date)s", {
            date: this.props.poll.poll_end_dt.toLocaleString(DateTime.DATETIME_MED),
        });
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

    onClickNumberOfVotes() {
        this.env.services.dialog.add(
            PollVotesPanel,
            { poll: this.props.poll },
            { rootRef: this.rootRef }
        );
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
}
