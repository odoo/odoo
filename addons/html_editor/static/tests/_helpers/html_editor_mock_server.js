import { onRpc } from "@web/../tests/web_test_helpers";

onRpc("res.lang", "get_installed", function getInstalled() {
    return [["en_US", "English (US)"]];
});

onRpc("/html_editor/icons_search", async (request) => {
    const { params } = await request.json();
    const needle = (params.needle || "").toLowerCase();
    const icons = ["check", "diamond", "eco", "favorite", "home", "search", "mail", "local_bar", "close", "bug_report", "oi_view-kanban"];
    return icons
        .filter((name) => !needle || name.includes(needle))
        .map((name) => ({ name, has_fill: true }));
});

onRpc("/html_editor/icons", () => [
    { name: "check", has_fill: false, tags: ["done", "ok", "validate"] },
    { name: "close", has_fill: false, tags: ["cancel", "x"] },
    { name: "diamond", has_fill: true, tags: ["gem", "jewel"] },
    { name: "favorite", has_fill: true, tags: ["heart", "love", "coeur"] },
    { name: "home", has_fill: true, tags: ["house"] },
    { name: "search", has_fill: false, tags: ["find", "magnifying glass"] },
    { name: "mail", has_fill: true, tags: ["email", "envelope"] },
    { name: "local_bar", has_fill: false, tags: ["drink", "cocktail"] },
    { name: "bug_report", has_fill: true, tags: ["insect"] },
    { name: "oi_view-kanban", has_fill: false, tags: ["view"] },
]);
