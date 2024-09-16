export default class Store {
    constructor() {
        this.setup();
    }
    setup() {
        this.url = "";
        this.base = {};
        this.update = 0;
        this.isLinux = false;
        this.advanced = false;
    }

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

            if (data.result.system === "Linux") {
                this.isLinux = true;
            }

            return data.result;
        } else if (method === "GET") {
            const response = await fetch(url);
            return await response.json();
        }

        return false;
    }
}
