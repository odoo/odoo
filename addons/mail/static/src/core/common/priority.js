import { Component } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @property {import('models').Thread} thread
 * @extends {Component<Props, Env>}
 */
export class Priority extends Component {
    static template = "mail.Priority";
    static props = ["thread"];

    get priorityDefinition() {
        return Object.fromEntries(this.props.thread.priority_definition);
    }

    get maxStar() {
        return Math.max(...Object.keys(this.priorityDefinition).map(Number));
    }

    get priority() {
        return Number(this.props.thread.priority);
    }

    get label() {
        return this.priorityDefinition[this.priority];
    }
}
