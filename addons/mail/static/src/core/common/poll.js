import { PollVotesPanel } from "@mail/core/common/poll_votes_panel";
import { propComputed } from "@mail/utils/common/hooks";
import { useDynamicInterval } from "@mail/utils/common/misc";

import { Component, proxy, signal, t } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

export class Poll extends Component {
    static template = "mail.Poll";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.poll = propComputed("poll", t.instanceOf(this.store["mail.poll"]));
        /** @type {import("@odoo/owl").Signal<Element>} */
        this.rootRef = signal();
        this.state = proxy({
            isShowingResults: false,
            selectedOptionIds: new Set(),
            voting: false,
        });
        useDynamicInterval(() => {
            const endDt = this.poll().poll_end_dt;
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
        });
    }

    get remainingTimeTextTitle() {
        if (!this.poll().poll_end_dt) {
            return "";
        }
        return _t("Poll ends on %(date)s", {
            date: this.poll().poll_end_dt.toLocaleString(DateTime.DATETIME_MED),
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
            this.poll().selfAlreadyVoted ||
            this.poll().end_message_id ||
            this.state.isShowingResults
        );
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ pollAtRender: import("models").MailPollModel }} param1
     */
    async onClickVote(ev, { pollAtRender }) {
        if (this.state.voting) {
            return;
        }
        try {
            this.state.voting = true;
            await pollAtRender.vote([...this.state.selectedOptionIds]);
        } finally {
            this.state.voting = false;
            this.state.selectedOptionIds.clear();
        }
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ pollAtRender: import("models").MailPollModel }} param1
     */
    onClickNumberOfVotes(ev, { pollAtRender }) {
        this.env.services.dialog.add(
            PollVotesPanel,
            { poll: pollAtRender },
            { rootRef: this.rootRef }
        );
    }

    /**
     * @param {Event} ev
     * @param {{ option: import("models").MailPollOptionModel, pollAtRender: import("models").MailPollModel }} param1
     */
    onOptionCheckboxToggle(ev, { option, pollAtRender }) {
        if (!pollAtRender.allow_multiple_options) {
            this.state.selectedOptionIds.clear();
        }
        if (ev.target.checked) {
            this.state.selectedOptionIds.add(option.id);
        } else {
            this.state.selectedOptionIds.delete(option.id);
        }
    }

    get voteButtonDisabled() {
        return this.state.selectedOptionIds.size === 0 || this.state.voting;
    }

    percentageAttStyle(option) {
        return this.isShowingResults ? `background-size: ${option.vote_percentage}%;` : "";
    }
}
