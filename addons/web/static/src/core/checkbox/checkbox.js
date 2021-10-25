/** @odoo-module **/

const { Component, QWeb } = owl;

/**
 * Custom checkbox
 *
 * <CheckBox
 *    value="boolean"
 *    disabled="boolean"
 *    t-on-change="_onValueChange"
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
}

CheckBox.template = "web.CheckBox";
CheckBox.nextId = 1;
CheckBox.props = {
    disabled: {
        type: Boolean,
        optional: true,
    },
    value: {
        type: Boolean,
        optional: true,
    },
};

QWeb.registerComponent("CheckBox", CheckBox);
