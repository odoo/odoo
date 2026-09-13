import { Deferred, expect, microTick, test } from "@odoo/hoot";
import { PosStockService } from "@point_of_sale/app/services/pos_stock_service";

function makeStockService() {
    const requests = [];
    const service = new PosStockService(
        {},
        {
            pos: { config: { id: 1 } },
            orm: {
                call(model, method, [ids]) {
                    const deferred = new Deferred();
                    requests.push({ ids, deferred });
                    return deferred;
                },
            },
        },
    );
    return { service, requests };
}

test("stock requests batch and deduplicate products already in flight", async () => {
    const { service, requests } = makeStockService();
    service.request([1, 2]);
    service.request([2, 3]);
    await microTick();
    service.request([1, 2, 3]);
    await microTick();
    expect(requests.map(({ ids }) => ids)).toEqual([[1, 2, 3]]);
    requests.forEach(({ deferred }) => deferred.resolve({ 1: 5, 2: 0, 3: 8 }));
    await microTick();
    expect(service.quantities).toEqual({ 1: 5, 2: 0, 3: 8 });
});

for (const staleFails of [false, true]) {
    test(`stock refresh supersedes an in-flight ${staleFails ? "failure" : "response"}`, async () => {
        const { service, requests } = makeStockService();
        service.request([1]);
        await microTick();
        service.refresh();
        await microTick();
        expect(requests.map(({ ids }) => ids)).toEqual([[1], [1]]);
        // Resolve in reverse order: a completed payment must keep the new stock.
        requests[1]?.deferred.resolve({ 1: 4 });
        await microTick();
        if (staleFails) {
            requests[0].deferred.reject(new Error("Old request failed"));
        } else {
            requests[0].deferred.resolve({ 1: 5 });
        }
        await microTick();
        expect(service.quantities[1]).toBe(4);
    });
}

test("older request cleanup cannot unlock a refreshed product", async () => {
    const { service, requests } = makeStockService();
    service.request([1]);
    await microTick();
    service.refresh();
    await microTick();
    requests[0].deferred.resolve({ 1: 10 });
    await microTick();
    service.request([1]);
    await microTick();
    expect(requests).toHaveLength(2);
    expect(service.quantities[1]).toBe(undefined);
    requests[1].deferred.resolve({ 1: 9 });
    await microTick();
    expect(service.quantities[1]).toBe(9);
});

test("refresh preserves queued, completed, missing and in-flight products", async () => {
    const { service, requests } = makeStockService();
    service.request([1]);
    await microTick();
    requests[0].deferred.resolve({ 1: 3 });
    await microTick();
    service.request([2]);
    await microTick();
    service.request([3]);
    service.refresh();
    service.refresh();
    await microTick();
    expect(requests).toHaveLength(3);
    expect([...requests[2].ids].sort()).toEqual([1, 2, 3]);
    requests[2].deferred.resolve({ 1: 0, 2: -1 });
    requests[1].deferred.resolve({ 2: 50 });
    await microTick();
    expect(service.quantities).toEqual({ 1: 0, 2: -1, 3: 0 });
});

test("a failed stock batch can be refreshed successfully", async () => {
    const { service, requests } = makeStockService();
    service.request([1]);
    await microTick();
    requests[0].deferred.reject(new Error("Offline"));
    await microTick();
    expect(service.quantities[1]).toBe(null);
    service.refresh();
    await microTick();
    requests[1].deferred.resolve({ 1: 0 });
    await microTick();
    expect(service.quantities[1]).toBe(0);
});
