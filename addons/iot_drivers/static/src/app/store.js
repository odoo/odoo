/* global owl */

const { Plugin, signal } = owl;

export default class Store extends Plugin {
    base = signal({});
    update = signal(0);
    isLinux = signal(false);
    advanced = signal(false);

    async rpc({ url, method = "GET", params = {} }) {
        if (method === "POST") {
            const response = await fetch(url, {
                method,
                headers: {
                    "Content-Type": "application/json; charset=utf-8",
                },
                body: JSON.stringify({
                    params,
                }),
            });

            const data = await response.json();
            return data.result;
        } else if (method === "GET") {
            const response = await fetch(url);
            return await response.json();
        }

        return false;
    }
}
