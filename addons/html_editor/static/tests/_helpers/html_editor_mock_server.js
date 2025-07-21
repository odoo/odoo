import { onRpc } from "@web/../tests/web_test_helpers";

onRpc("res.lang", "get_installed", function getInstalled() {
    return [["en_US", "English (US)"]];
});
