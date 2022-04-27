/** @odoo-module **/
import { TagItem } from "./tag_item";

const { Component } = owl;

export class TagsList extends Component {
    get visibleTags() {
        if (this.props.visibleTags && this.props.tags.length > this.props.visibleTags) {
            return this.props.tags.slice(0, this.props.visibleTags - 1);
        }
        return this.props.tags;
    }
    get otherTags() {
        if (!this.props.visibleTags || this.props.tags.length <= this.props.visibleTags) return;
        return this.props.tags.slice(this.props.visibleTags - 1);
    }
    get tooltip() {
        return this.otherTags.map((i) => i.text).join("<br/>");
    }
}
TagsList.components = {
    TagItem,
};
TagsList.template = "web.TagsList";
TagsList.defaultProps = {
    className: "",
};
TagsList.props = {
    className: { type: String, optional: true },
    name: { type: String, optional: true },
    visibleTags: { type: Number, optional: true },
    slots: { type: Object, optional: true },
    tags: { type: Object, optional: true },
};
