import { Component, useEffect, useRef } from "@odoo/owl";
import { useDropdownCloser } from "@web/core/dropdown/dropdown_hooks";

export class KanbanDropdownMenuWrapper extends Component {
    static template = "web.KanbanDropdownMenuWrapper";
    static props = {
        slots: Object,
    };

    setup() {
        this.dropdownControl = useDropdownCloser();
        this.rootRef = useRef("rootRef");
        useEffect(() => {
            const dropdownEls = this.rootRef.el.querySelectorAll(".dropdown-item");
            dropdownEls.forEach((el) => el.classList.add("o-navigable"));
        });
    }

    onClick(ev) {
        this.dropdownControl.closeAll();
    }
}
