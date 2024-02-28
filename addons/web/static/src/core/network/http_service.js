/** @odoo-module **/

import { registry } from "../registry";

function checkResponseStatus(response) {
    if (response.status === 502) {
        throw new Error("Failed to fetch");
    }
}

export const httpService = {
    start() {
        return {
            async get(route, readMethod = "json") {
                const response = await fetch(route, { method: "GET" });
                checkResponseStatus(response);
                return response[readMethod]();
            },
            async post(route, params = {}, readMethod = "json") {
                const formData = new FormData();
                for (const key in params) {
                    const value = params[key];
                    if (Array.isArray(value) && value.length) {
                        for (const val of value) {
                            formData.append(key, val);
                        }
                    } else {
                        formData.append(key, value);
                    }
                }
                const info = {
                    body: formData,
                    method: "POST",
                };
                const response = await fetch(route, info);
                checkResponseStatus(response);
                return response[readMethod]();
            },
        };
    },
};

registry.category("services").add("http", httpService);
