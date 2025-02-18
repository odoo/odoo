import { Component, useEffect, useState } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @property {import("models").Poll} poll
 * @extends {Component<Props, Env>}
 */
export class Poll extends Component {
    static template = "mail.Poll";
    static props = {
        poll: Object,
    };
    static components = {};

    setup() {
        this.state = useState({
            showResults: false,
            checkedByAnswerId: {},
        });
        useEffect(
            (alreadyVoted, closed) => {
                this.state.showResults = alreadyVoted || closed;
            },
            () => [this.props.poll.selfAlreadyVoted, this.props.poll.closed]
        );
    }

    toggleShowResults() {
        this.state.checkedByAnswerId = {};
        this.state.showResults = !this.state.showResults;
    }

    onClickVote() {
        const selectedAnswerIds = [];
        for (const [answerId, checked] of Object.entries(this.state.checkedByAnswerId)) {
            if (checked) {
                selectedAnswerIds.push(answerId);
            }
        }
        this.props.poll.vote(selectedAnswerIds);
    }

    get voteButtonDisabled() {
        return !Object.values(this.state.checkedByAnswerId).some(Boolean);
    }

    percentageAttStyle(answer) {
        return this.state.showResults ? `background-size: ${answer.percentage}%;` : "";
    }
}
