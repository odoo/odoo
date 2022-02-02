/** @odoo-module **/

const { Component } = owl;

/**
 * Custom checkbox
 *
 * <CheckBox
 *    value="boolean"
 *    disabled="boolean"
 *    onChange="_onValueChange"
 *    >
 *    Change the label text
 *  </CheckBox>
 *
 * @extends Component
 */

export class CheckBox extends Component {
    setup() {
        this.id = `checkbox-comp-${CheckBox.nextId++}`;
    }
    onChange(ev) {
        if (this.props.onChange) {
            this.props.onChange(ev);
        }
    }
}

CheckBox.template = "web.CheckBox";
CheckBox.nextId = 1;
owl.Component._components.CheckBox = CheckBox;
