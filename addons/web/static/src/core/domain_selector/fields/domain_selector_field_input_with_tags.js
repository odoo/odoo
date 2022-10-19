/** @odoo-module **/

import { Component, useRef } from "@odoo/owl";

export class DomainSelectorFieldInputWithTags extends Component {
    setup() {
        this.inputRef = useRef("input");
    }

    removeTag(tagIndex) {
        const value = [...this.props.value];
        value.splice(tagIndex, 1);
        this.props.update({ value });
    }
    addTag(value) {
        this.props.update({ value: this.props.value.concat(value) });
    }

    onBtnClick() {
        const value = this.inputRef.el.value;
        this.inputRef.el.value = "";
        this.addTag(value);
    }
}
DomainSelectorFieldInputWithTags.template = "web.DomainSelectorFieldInputWithTags";
