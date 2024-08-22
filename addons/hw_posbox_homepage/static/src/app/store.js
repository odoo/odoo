export default class Store {
    constructor() {
        this.setup();
    }
    LogsPage
    setup() {
        this.url = "";
        this.base = {};
        this.update = 0;
        this.advanced = false;
    }

    async rpc({ url, method = "GET", params = {} }) {
        url = "http://10.50.82.98" + url;

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
            console.info("RPC Response", data.result);

            return data.result;
        } else if (method === "GET") {
            const response = await fetch(url);
            return await response.json();
        }

        return false;
    }
}
