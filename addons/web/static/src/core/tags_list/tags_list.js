import { Component } from "@odoo/owl";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { useState } from "@web/owl2/utils";

export class TagsList extends Component {
    static template = "web.TagsList";
    static components = { BadgeTag };
    static props = {
        slots: { type: Object },
        tags: { type: Array, element: Object },
        tagLimit: { type: Number },
    };

    setup() {
        this.state = useState({ expanded: false });
    }

    get invisibleTags() {
        return this.props.tags.slice(this.visibleTagCount);
    }

    showAllTags() {
        this.state.expanded = true;
    }

    get visibleTagCount() {
        if (this.state.expanded) {
            return this.props.tags.length;
        }
        // remove an item to display the counter instead
        const counter = this.props.tags.length > this.props.tagLimit ? 1 : 0;
        return this.props.tagLimit - counter;
    }

    get visibleTags() {
        return this.props.tags.slice(0, this.visibleTagCount);
    }
}
