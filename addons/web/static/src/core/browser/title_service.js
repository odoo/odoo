import { registry } from "../registry";

export const titleService = {
    start() {
        const titleParts = {};

        function getParts() {
            return Object.assign({}, titleParts);
        }

        function setParts(parts) {
            for (const key in parts) {
                const val = parts[key];
                if (!val) {
                    delete titleParts[key];
                } else {
                    titleParts[key] = val;
                }
            }
            document.title = Object.values(titleParts).join(" - ") || "Odoo";
        }

        return {
            /**
             * @returns {string}
             */
            get current() {
                return document.title;
            },
            getParts,
            setParts,
        };
    },
};

registry.category("services").add("title", titleService);
