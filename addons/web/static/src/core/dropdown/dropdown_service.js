/** @odoo-module **/

import { registry } from "@web/core/registry";

export const dropdownService = {
    start(env) {
        const dropdowns = {};
        let dropdownId = 0;
        let currentDropdown = undefined;

        function add(dropdown) {
            const id = ++dropdownId;
            dropdowns[id] = dropdown;
            return id;
        }

        function remove(id) {
            if (dropdowns[id]) {
                if (dropdowns[id].isOpen) {
                    dropdowns[id].updateState(false);
                }
                delete dropdowns[id];
            }
        }

        function open(id) {
            for (const key in dropdowns) {
                if (key !== id && dropdowns[key] && dropdowns[key].isOpen) {
                    dropdowns[key].updateState(false);
                }
            }

            if (dropdowns[id]) {
                dropdowns[id].updateState(true);
                currentDropdown = dropdowns[id];
            }
        }

        function close(id) {
            if (dropdowns[id]) {
                dropdowns[id].updateState(false);
                if (currentDropdown === dropdowns[id]) {
                    currentDropdown = undefined;
                }
            }
        }

        function handleOutsideEvent(event) {
            if (currentDropdown) {
                currentDropdown.onWindowClicked(event);
            }
        }

        window.addEventListener("click", handleOutsideEvent);
        window.addEventListener("scroll", handleOutsideEvent, true);

        return {
            add,
            remove,
            open,
            close,
        };
    },
};

registry.category("services").add("dropdown", dropdownService);
