/** @odoo-module **/

const { Component } = owl;

export class TagItem extends Component {}

TagItem.template = "web.TagItem";
TagItem.defaultProps = {
    colorIndex: 0,
    className: "",
    handlesColor: false,
    onClick: () => {},
};
TagItem.props = {
    colorIndex: { optional: true },
    className: { type: String, optional: true },
    handlesColor: { type: Boolean, optional: true },
    id: { type: String, optional: true },
    img: { type: String, optional: true },
    onClick: { type: Function, optional: true },
    onDelete: { type: Function, optional: true },
    text: { type: String, optional: true },
};
