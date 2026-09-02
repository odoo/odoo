import { onRpc } from "@web/../tests/web_test_helpers";

onRpc("res.lang", "get_installed", function getInstalled() {
    return [["en_US", "English (US)"]];
});

onRpc("/html_editor/icons_search", async (request) => {
    const { params } = await request.json();
    const needle = (params.needle || "").toLowerCase();
    const icons = ["check", "diamond", "eco", "favorite", "home", "search", "mail", "local_bar", "close", "bug_report"];
    return icons
        .filter((name) => !needle || name.includes(needle))
        .map((name) => ({ name, has_fill: true }));
});
