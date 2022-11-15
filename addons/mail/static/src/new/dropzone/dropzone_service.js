/** @odoo-module **/

import { registry } from "@web/core/registry";

import { DropzoneContainer } from "@mail/new/dropzone/dropzone_container";

export const dropzoneService = {
    start() {
        const dropzones = new Set();
        registry.category("main_components").add("mail.DropzoneContainer", {
            Component: DropzoneContainer,
            props: { dropzones },
        });

        let lastId = 0;

        function add(target) {
            const dropzone = {
                id: lastId++,
                ref: target,
            };
            dropzones.add(dropzone);
            return () => remove(dropzone);
        }

        function remove(dropzone) {
            dropzones.delete(dropzone);
        }

        return { add };
    },
};

registry.category("services").add("dropzone", dropzoneService);
