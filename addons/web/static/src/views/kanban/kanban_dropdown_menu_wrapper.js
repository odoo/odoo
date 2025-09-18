// @ts-check

/** @module @web/views/kanban/kanban_dropdown_menu_wrapper - Wrapper adding keyboard navigation classes and close-on-click to kanban dropdown menus */

import { Component, useEffect, useRef } from "@odoo/owl";
import { useDropdownCloser } from "@web/components/dropdown/dropdown_hooks";
/**
 * Wrapper around kanban record dropdown menus.
 *
 * Adds the `o-navigable` CSS class to all `.dropdown-item` elements so
 * keyboard navigation works, and closes the parent dropdown on item click.
 */
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

    /**
     * Close all ancestor dropdowns when a menu item is clicked.
     * @param {MouseEvent} ev
     */
    onClick(ev) {
        this.dropdownControl.closeAll();
    }
}
