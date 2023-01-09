/** @odoo-module **/

import { Component } from "@odoo/owl";

export class TagsList extends Component {
    get visibleTags() {
        if (this.props.itemsVisible && this.props.tags.length > this.props.itemsVisible) {
            return this.props.tags.slice(0, this.props.itemsVisible - 1);
        }
        return this.props.tags;
    }
    get otherTags() {
        if (!this.props.itemsVisible || this.props.tags.length <= this.props.itemsVisible) {
            return [];
        }
        return this.props.tags.slice(this.props.itemsVisible - 1);
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
TagsList.template = "web.TagsList";
TagsList.defaultProps = {
    className: "",
    displayBadge: true,
    displayText: true,
};
TagsList.props = {
    className: { type: String, optional: true },
    displayBadge: { type: Boolean, optional: true },
    displayText: { type: Boolean, optional: true },
    name: { type: String, optional: true },
    itemsVisible: { type: Number, optional: true },
    tags: { type: Object, optional: true },
};
