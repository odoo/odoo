/** @odoo-module **/

import { Component, useRef } from "@odoo/owl";

export class PdfGroupName extends Component {
    static props = {
        groupId: String,
        name: String,
        edit: Boolean,
        onToggleEdit: {
            type: Function,
            optional: true,
        },
        onEditName: {
            type: Function,
            optional: true,
        },
    };
    static template = "documents.component.PdfGroupName";

    setup() {
        // used to get the value of the input when renaming.
        this.nameInputRef = useRef("nameInput");
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @public
     */
    onBlur() {
        this.props.onEditName(this.props.groupId, this.nameInputRef.el.value);
    }
    /**
     * @public
     */
    onClickGroupName() {
        this.props.onToggleEdit(this.props.groupId, true);
    }
    /**
     * @public
     * @param {MouseEvent} ev
     */
    onKeyDown(ev) {
        if (ev.code !== "Enter") {
            return;
        }
        ev.stopPropagation();
        this.props.onEditName(this.props.groupId, this.nameInputRef.el.value);
        this.props.onToggleEdit(this.props.groupId, false);
    }
}
