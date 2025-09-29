import { Component } from "@odoo/owl";

export class TagsList extends Component {
    static template = "web.TagsList";
    static props = {
        slots: { type: Object },
        tags: { type: Array, element: Object },
        mapTooltip: { type: Function, optional: true }, // not great but does the job for now
        visibleItemsLimit: { type: Number },
    };
    static defaultProps = {
        mapTooltip: (tag) => tag.tooltip || tag.text,
    };

    get invisibleTags() {
        return this.props.tags.slice(this.visibleTagCount);
    }

    get tooltipInfo() {
        return JSON.stringify({
            tags: this.invisibleTags.map((tag) => this.props.mapTooltip(tag)),
        });
    }

    get visibleTagCount() {
        // remove an item to display the counter instead
        const counter = this.props.tags.length > this.props.visibleItemsLimit ? 1 : 0;
        return this.props.visibleItemsLimit - counter;
    }

    get visibleTags() {
        return this.props.tags.slice(0, this.visibleTagCount);
    }
}
