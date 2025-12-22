import { Component } from "@odoo/owl";

export class TagsList extends Component {
    static template = "web.TagsList";
    static defaultProps = {
        displayText: true,
    };
    static props = {
        displayText: { type: Boolean, optional: true },
        visibleItemsLimit: { type: Number, optional: true },
        tags: { type: Object },
    };
    get visibleTagsCount() {
        return this.props.visibleItemsLimit - 1;
    }
    get visibleTags() {
        if (this.props.visibleItemsLimit && this.props.tags.length > this.props.visibleItemsLimit) {
            return this.props.tags.slice(0, this.visibleTagsCount);
        }
        return this.props.tags;
    }
    get otherTags() {
        if (
            !this.props.visibleItemsLimit ||
            this.props.tags.length <= this.props.visibleItemsLimit
        ) {
            return [];
        }
        return this.props.tags.slice(this.visibleTagsCount);
    }
    get tooltipInfo() {
        return JSON.stringify({
            tags: this.otherTags.map((tag) => ({
                text: tag.text,
                id: tag.id,
            })),
        });
    }
}
