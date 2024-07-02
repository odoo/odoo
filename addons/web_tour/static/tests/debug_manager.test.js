import { Component, xml } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { DebugMenu } from "@web/core/debug/debug_menu";
import { registry } from "@web/core/registry";
import { disableTours } from "@web_tour/debug/debug_manager";
import {
    contains,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { beforeEach, expect, test } from "@odoo/hoot";

class DebugMenuParent extends Component {
    static template = xml`<DebugMenu/>`;
    static components = { DebugMenu };
    static props = ["*"];
    setup() {
        useOwnDebugContext({ categories: ["default", "custom"] });
    }
}

const debugRegistry = registry.category("debug").category("default");

beforeEach(() => {
    const entries = debugRegistry.getEntries();
    for (const [key] of entries) {
        debugRegistry.remove(key);
    }
});

test("web_tour: can disable tours", async () => {
    // TODO: should be removed after Hoot MAJ (JUM) !
    const fakeLocalStorage = {
        tour__sampletour1__currentIndex: "0",
        tour__sampletour1__stepDelay: "0",
        tour__sampletour1__keepWatchBrowser: "0",
        tour__sampletour1__showPointerDuration: "0",
        tour__sampletour1__mode: "manual",
        tour__sampletour2__currentIndex: "0",
        tour__sampletour2__stepDelay: "0",
        tour__sampletour2__keepWatchBrowser: "0",
        tour__sampletour2__showPointerDuration: "0",
        tour__sampletour2__mode: "manual",
    };
    Object.defineProperties(fakeLocalStorage, {
        getItem: {
            value(key) {
                return fakeLocalStorage[key];
            },
        },
        removeItem: {
            value(key) {
                delete fakeLocalStorage[key];
            },
        },
    });
    patchWithCleanup(browser, { localStorage: fakeLocalStorage });
    debugRegistry.add("web_tour.disableTours", disableTours);
    onRpc("check_access_rights", () => {
        return true;
    });
    onRpc("consume", ({ args }) => {
        expect.step(args[0]);
        return true;
    });
    await mountWithCleanup(DebugMenuParent);
    await contains("button.dropdown-toggle").click();
    expect(".dropdown-item").toHaveCount(1);
    await contains(".dropdown-item").click();
    expect.verifySteps([["sampletour1", "sampletour2"]]);
});
