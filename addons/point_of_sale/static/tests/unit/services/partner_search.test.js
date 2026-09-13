import { Deferred, expect, test } from "@odoo/hoot";
import { animationFrame, click } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { MainComponentsContainer } from "@web/ui/main_components_container";

import { definePosModels } from "../data/generate_model_definitions.js";
import { setupPosEnv } from "../utils.js";

definePosModels();

async function setupPartnerList() {
    const store = await setupPosEnv();
    let list;
    patchWithCleanup(PartnerList.prototype, {
        setup() {
            super.setup();
            list = this;
        },
    });
    await mountWithCleanup(MainComponentsContainer);
    store.dialog.add(PartnerList, { getPayload() {} });
    await animationFrame();
    const requests = [];
    patchWithCleanup(store.data, {
        callRelated(model, method, args) {
            const response = new Deferred();
            requests.push({ args, response });
            return response;
        },
    });
    return { list, requests };
}

test("a delayed partner page advances the offset for its original search", async () => {
    const { list, requests } = await setupPartnerList();
    list.state.query = "Alice";
    const alice = list.pos.models["res.partner"].create({ id: 10007, name: "Alice" });
    const loading = list.getNewPartners();
    expect(requests[0].args[1].find((term) => term[0] === "name")).toEqual([
        "name",
        "ilike",
        "Alice%",
    ]);
    expect(requests[0].args[2]).toBe(0);
    list.state.query = "Bob";
    requests[0].response.resolve({ "res.partner": [alice] });
    await loading;
    expect(list.globalState.offsetBySearch.Alice).toBe(1);
    expect(list.globalState.offsetBySearch.Bob).toBe(undefined);
    expect(list.state.loadedPartners.map((partner) => partner.id)).toEqual([10007]);
});

test("repeated partner searches share an in-flight page", async () => {
    const { list, requests } = await setupPartnerList();
    list.state.query = "Alice";
    const first = list.getNewPartners();
    const second = list.getNewPartners();
    expect(requests).toHaveLength(1);
    requests.forEach(({ response }) => response.resolve({ "res.partner": [] }));
    await Promise.all([first, second]);
    expect(list.state.loading).toBe(false);
});

test("finishing an older search leaves a newer search loading", async () => {
    const { list, requests } = await setupPartnerList();
    list.state.query = "Alice";
    const first = list.getNewPartners();
    list.state.query = "Bob";
    const second = list.getNewPartners();
    requests[0].response.resolve({ "res.partner": [] });
    await first;
    expect(list.state.loading).toBe(true);
    requests[1].response.resolve({ "res.partner": [] });
    await second;
    expect(list.state.loading).toBe(false);
    expect(list.globalState.offsetBySearch.Alice).toBe(0);
    expect(list.globalState.offsetBySearch.Bob).toBe(0);
});

test("changing the query suppresses a stale search notification", async () => {
    const { list, requests } = await setupPartnerList();
    patchWithCleanup(list.notification, { add: () => expect.step("notification") });
    if (list.ui.isSmall) {
        await click(".modal-header button:has(.fa-magnifying-glass)");
        await animationFrame();
    }
    list.searchInputRef.el.value = "Alice";
    const search = list.onEnter();
    list.state.query = "Bob";
    requests[0].response.resolve({ "res.partner": [] });
    await search;
    expect.verifySteps([]);
});

test("a failed partner request releases the page for retry", async () => {
    const { list, requests } = await setupPartnerList();
    list.state.query = "Alice";
    const first = list.getNewPartners();
    const failure = new Error("Offline");
    const rejected = first.catch((error) => error);
    requests[0].response.reject(failure);
    expect(await rejected).toBe(failure);
    expect(list.state.loading).toBe(false);
    const retry = list.getNewPartners();
    expect(requests).toHaveLength(2);
    expect(requests[1].args[2]).toBe(0);
    requests[1].response.resolve({ "res.partner": [] });
    await retry;
    expect(list.state.loading).toBe(false);
});

test("an empty page exhausts only its query even with many cached partners", async () => {
    const { list, requests } = await setupPartnerList();
    for (let id = 10000; id < 10200; id++) {
        list.loadedPartnerIds.add(id);
    }
    list.state.query = "Alice";
    const first = list.getNewPartners();
    requests[0].response.resolve({ "res.partner": [] });
    await first;
    const again = list.getNewPartners();
    expect(requests).toHaveLength(1);
    requests
        .slice(1)
        .forEach(({ response }) => response.resolve({ "res.partner": [] }));
    await again;
    list.state.query = "Bob";
    const other = list.getNewPartners();
    expect(requests.at(-1).args[1].find((term) => term[0] === "name")).toEqual([
        "name",
        "ilike",
        "Bob%",
    ]);
    requests.at(-1).response.resolve({ "res.partner": [] });
    await other;
});

for (const query of ["constructor", "__proto__"]) {
    test(`searching for ${query} uses numeric pagination`, async () => {
        const { list, requests } = await setupPartnerList();
        list.state.query = query;
        const first = list.getNewPartners();
        expect(requests[0].args[2]).toBe(0);
        const partner = list.state.initialPartners[0];
        requests[0].response.resolve({ "res.partner": [partner] });
        await first;
        const second = list.getNewPartners();
        expect(requests[1].args[2]).toBe(1);
        requests[1].response.resolve({ "res.partner": [] });
        await second;
    });
}

test("closing the dialog cancels a pending scroll fetch", async () => {
    const { list, requests } = await setupPartnerList();
    list.modalContent.dispatchEvent(new Event("scroll"));
    list.props.close();
    await animationFrame();
    await advanceTime(300);
    expect(requests).toHaveLength(0);
    requests.forEach(({ response }) => response.resolve({ "res.partner": [] }));
});

test("closing the dialog suppresses a pending search notification", async () => {
    const { list, requests } = await setupPartnerList();
    patchWithCleanup(list.notification, { add: () => expect.step("notification") });
    if (list.ui.isSmall) {
        await click(".modal-header button:has(.fa-magnifying-glass)");
        await animationFrame();
    }
    list.searchInputRef.el.value = "Alice";
    const search = list.onEnter();
    list.props.close();
    await animationFrame();
    requests[0].response.resolve({ "res.partner": [] });
    await search;
    expect.verifySteps([]);
});

test("a failed search reports failure rather than an empty result", async () => {
    const { list, requests } = await setupPartnerList();
    const notifications = [];
    patchWithCleanup(list.notification, {
        add: (message, options) => notifications.push({ message, options }),
    });
    if (list.ui.isSmall) {
        await click(".modal-header button:has(.fa-magnifying-glass)");
        await animationFrame();
    }
    list.searchInputRef.el.value = "Alice";
    const search = list.onEnter();
    requests[0].response.reject(new Error("Offline"));
    await search;
    expect(notifications).toHaveLength(1);
    expect(notifications[0].options?.type).toBe("warning");
    expect(notifications[0].message).toBe("Customer search failed. Please try again.");
    expect(list.state.loading).toBe(false);
});

test("a failed scroll fetch is handled and can be retried", async () => {
    const { list, requests } = await setupPartnerList();
    list.modalContent.dispatchEvent(new Event("scroll"));
    await advanceTime(300);
    expect(requests).toHaveLength(1);
    requests[0].response.reject(new Error("Offline"));
    await animationFrame();
    expect(list.state.loading).toBe(false);
    list.modalContent.dispatchEvent(new Event("scroll"));
    await advanceTime(300);
    expect(requests).toHaveLength(2);
    requests[1].response.resolve({ "res.partner": [] });
    await animationFrame();
    expect(list.state.loading).toBe(false);
});
