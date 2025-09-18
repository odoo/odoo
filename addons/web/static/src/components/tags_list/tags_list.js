// @ts-check

/** @module @web/components/tags_list/tags_list - Renders a list of colored tags with optional visibility limit and overflow counter */

import { Component } from "@odoo/owl";

export class TagsList extends Component {
    static template = "web.TagsList";
    static defaultProps = {
        displayText: true,
    };
    static props = {
        displayText: { type: Boolean, optional: true },
        visibleItemsLimit: { type: Number, optional: true },
        tags: { type: Array, element: Object },
    };

    /** @returns {number} maximum number of tags shown before collapsing */
    get visibleTagsCount() {
        return this.props.visibleItemsLimit - 1;
    }
    /** @returns {Object[]} tags visible within the limit */
    get visibleTags() {
        if (
            this.props.visibleItemsLimit &&
            this.props.tags.length > this.props.visibleItemsLimit
        ) {
            return this.props.tags.slice(0, this.visibleTagsCount);
        }
        return this.props.tags;
    }
    /** @returns {Object[]} overflow tags hidden behind the "+N" badge */
    get otherTags() {
        if (
            this.props.visibleItemsLimit &&
            this.props.tags.length > this.props.visibleItemsLimit
        ) {
            return this.props.tags.slice(this.visibleTagsCount);
        }
        return [];
    }
    /** @returns {string} JSON-encoded tooltip payload for overflow tags */
    get tooltipInfo() {
        return JSON.stringify({
            tags: this.otherTags.map((tag) => ({
                text: tag.text,
                id: tag.id,
            })),
        });
    }
}
