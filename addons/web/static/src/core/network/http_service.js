/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "../registry";

function checkResponseStatus(response) {
    if (response.status === 502) {
        throw new Error("Failed to fetch");
    }
}

export async function get(route, readMethod = "json") {
    const response = await browser.fetch(route, { method: "GET" });
    checkResponseStatus(response);
    return response[readMethod]();
}

export async function post(route, params = {}, readMethod = "json") {
    const formData = new FormData();
    for (const key in params) {
        formData.append(key, params[key]);
    }
    const response = await browser.fetch(route, {
        body: formData,
        method: "POST",
    });
    checkResponseStatus(response);
    return response[readMethod]();
}

export const httpService = {
    start() {
        return { get, post };
    },
};

registry.category("services").add("http", httpService);
