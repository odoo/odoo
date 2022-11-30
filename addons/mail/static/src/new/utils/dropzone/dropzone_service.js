/** @odoo-module **/

import { DropzoneContainer } from "@mail/new/utils/dropzone/dropzone_container";

import { registry } from "@web/core/registry";

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
