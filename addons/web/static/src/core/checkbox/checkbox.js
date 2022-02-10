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
}

CheckBox.template = "web.CheckBox";
CheckBox.nextId = 1;
CheckBox.defaultProps = {
    onChange: () => {},
    onKeydown: () => {},
};
CheckBox.props = {
    id: {
        type: true,
        optional: true,
    },
    disabled: {
        type: Boolean,
        optional: true,
    },
    value: {
        type: Boolean,
        optional: true,
    },
    slots: {
        type: Object,
        optional: true,
    },
    onChange: {
        type: Function,
        optional: true,
    },
    onKeydown: {
        type: Function,
        optional: true,
    },
};
