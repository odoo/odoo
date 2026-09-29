import { registry } from "@web/core/registry";

const originalFetch = window.fetch;

function waitForRequest(url) {
    return new Promise((resolve, reject) => {
        window.fetch = async (...args) => {
            const response = await originalFetch(...args);
            if (args[0].includes(url)) {
                window.fetch = originalFetch;
                resolve(response);
            }
            return response;
        };
    });
}

function authorizeRPC(authorize) {
    return {
        content: "Check RPC",
        trigger: 'body',
        run: async () => {
            const response = await fetch("/web/session/check", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({ params: {} }),
            });
            const result = response.json();
            const isBlocked = result?.error?.data?.name === "odoo.http.session.CheckIdentityException"
            if ((authorize && !isBlocked) || (!authorize && isBlocked)) return;
            throw new Error("RPC authorization is not being handled correctly");
        },
    }
}

function login(login, password) {
    return [
        {
            content: "Login input is empty",
            trigger: "input#login:empty",
        },
        {
            content: "Password input is empty",
            trigger: "input#password:empty",
        },
        {
            content: "Edit the login",
            trigger: "input#login",
            run: `edit ${login}`,
        },
        {
            content: "Edit the password",
            trigger: "input#password",
            run: `edit ${password}`,
        },
        {
            content: "Click on login button",
            trigger: 'button:contains("Log in")',
            run: "click",
            expectUnloadPage: true,
        },
    ];
}

registry.category("web_tour.tours").add("test_login_check_identity", {
    url: "/web/login",
    steps: () => [
        ...login("user", "user"),
        {
            content: "Assert fingerprint updated in the session",
            trigger: 'body',
            run: async () => {
                await waitForRequest('/web/session/fingerprint/check');
            },
        },
        authorizeRPC(true),
    ],
});
