/** @odoo-module **/

import { Component } from "@odoo/owl";

export class TagsList extends Component {
    static template = "web.TagsList";
    static defaultProps = {
        displayText: true,
    };
    static props = {
        displayText: { type: Boolean, optional: true },
        itemsVisible: { type: Number, optional: true },
        tags: { type: Object },
    };
    get visibleTagsCount() {
        return this.props.itemsVisible - 1;
    }
    get visibleTags() {
        if (this.props.itemsVisible && this.props.tags.length > this.props.itemsVisible) {
            return this.props.tags.slice(0, this.visibleTagsCount);
        }
        return this.props.tags;
    }
    get otherTags() {
        if (!this.props.itemsVisible || this.props.tags.length <= this.props.itemsVisible) {
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
