import { Deferred, expect, test } from "@odoo/hoot";
import { Component, reactive, xml } from "@odoo/owl";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { ConnectionLostError } from "@web/core/network";

definePosModels();

async function setupRefresh() {
    const pos = await setupPosEnv();
    const preset = pos.models["pos.preset"].get(2);
    preset.slots_per_interval = 1;
    const slots = Object.values(preset.availabilities).flatMap(Object.values);
    const slot = slots[0];
    const date = slot.datetime.toISODate();
    const key = slot.datetime.toFormat("yyyy-MM-dd HH:mm:ss");
    const utcKey = slot.datetime.toUTC().toFormat("yyyy-MM-dd HH:mm:ss");
    const requests = [];
    patchWithCleanup(pos.data, {
        call(model, method, args) {
            expect([model, method]).toEqual(["pos.preset", "get_available_slots"]);
            const request = new Deferred();
            requests.push({ request, id: args[0] });
            return request;
        },
    });
    return {
        pos,
        preset,
        slots,
        key,
        requests,
        current: () => preset.availabilities[date][key],
        response: (ids) => ({ usage_utc: { [utcKey]: ids } }),
    };
}

test("failed refresh retains known server bookings and includes new local orders", async () => {
    const { pos, preset, slots, key, requests, current } = await setupRefresh();
    preset.computeAvailabilities({ [key]: [9001] });
    const local = pos.addNewOrder({
        preset_id: preset,
        preset_time: slots[1].datetime,
    });
    const refreshing = pos.syncPresetSlotAvaibility(preset);
    requests[0].request.reject(new ConnectionLostError());
    await refreshing;
    expect([...current().order_ids]).toEqual([9001]);
    expect(current().isFull).toBe(true);
    const localSlot =
        preset.availabilities[slots[1].datetime.toISODate()][
            slots[1].datetime.toFormat("yyyy-MM-dd HH:mm:ss")
        ];
    expect([...localSlot.order_ids]).toEqual([local.id]);
});

for (const oldFails of [false, true]) {
    test(`late ${oldFails ? "failure" : "success"} cannot replace a newer refresh`, async () => {
        const { pos, preset, requests, current, response } = await setupRefresh();
        const first = pos.syncPresetSlotAvaibility(preset);
        const second = pos.syncPresetSlotAvaibility(preset);
        requests[1].request.resolve(response([9002]));
        await second;
        if (oldFails) {
            requests[0].request.reject(new ConnectionLostError());
        } else {
            requests[0].request.resolve(response([9001]));
        }
        await first;
        expect([...current().order_ids]).toEqual([9002]);
        expect(current().isFull).toBe(true);
    });
}

test("successful empty refresh clears old server bookings", async () => {
    const { pos, preset, key, requests, current } = await setupRefresh();
    preset.computeAvailabilities({ [key]: [9001] });
    const refreshing = pos.syncPresetSlotAvaibility(preset);
    requests[0].request.resolve({ usage_utc: {} });
    await refreshing;
    expect([...current().order_ids]).toEqual([]);
    expect(current().isFull).toBe(false);
});

test("failure before the first server response still computes local availability", async () => {
    const { pos, preset, slots, requests, current } = await setupRefresh();
    const local = pos.addNewOrder({
        preset_id: preset,
        preset_time: slots[0].datetime,
    });
    const refreshing = pos.syncPresetSlotAvaibility(preset);
    requests[0].request.reject(new ConnectionLostError());
    await refreshing;
    expect([...current().order_ids]).toEqual([local.id]);
    expect(current().isFull).toBe(true);
});

test("newer failure retains the known snapshot and a subsequent retry can replace it", async () => {
    const { pos, preset, key, requests, current, response } = await setupRefresh();
    preset.computeAvailabilities({ [key]: [9000] });
    const first = pos.syncPresetSlotAvaibility(preset);
    const second = pos.syncPresetSlotAvaibility(preset);
    requests[1].request.reject(new ConnectionLostError());
    await second;
    requests[0].request.resolve(response([9001]));
    await first;
    expect([...current().order_ids]).toEqual([9000]);
    const retry = pos.syncPresetSlotAvaibility(preset);
    requests[2].request.resolve(response([9003]));
    await retry;
    expect([...current().order_ids]).toEqual([9003]);
});

test("refreshes for different presets do not supersede one another", async () => {
    const { pos, preset, key, requests, current, response } = await setupRefresh();
    const other = pos.models["pos.preset"].get(1);
    const first = pos.syncPresetSlotAvaibility(preset);
    const second = pos.syncPresetSlotAvaibility(other);
    expect(requests.map(({ id }) => id)).toEqual([preset.id, other.id]);
    requests[1].request.resolve(response([9002]));
    await second;
    requests[0].request.resolve(response([9001]));
    await first;
    expect([...current().order_ids]).toEqual([9001]);
    expect(other.uiState.serverUsage[key]).toEqual([9002]);
});

test("different observers of the same preset share refresh ordering", async () => {
    const { pos, preset, requests, current, response } = await setupRefresh();
    const firstObserver = reactive(preset, () => {});
    const secondObserver = reactive(preset, () => {});
    expect(firstObserver).not.toBe(secondObserver);
    const first = pos.syncPresetSlotAvaibility(firstObserver);
    const second = pos.syncPresetSlotAvaibility(secondObserver);
    requests[1].request.resolve(response([9002]));
    await second;
    requests[0].request.resolve(response([9001]));
    await first;
    expect([...current().order_ids]).toEqual([9002]);
});

test("mounted POS consumers share refresh ordering for the same record", async () => {
    const { requests, current, response } = await setupRefresh();
    class Consumer extends Component {
        static props = {};
        static template = xml`<div/>`;
        setup() {
            this.pos = usePos();
        }
        get preset() {
            return this.pos.models["pos.preset"].get(2);
        }
        refresh() {
            return this.pos.syncPresetSlotAvaibility(this.preset);
        }
    }
    const firstConsumer = await mountWithCleanup(Consumer);
    const secondConsumer = await mountWithCleanup(Consumer);
    expect(firstConsumer.preset).not.toBe(secondConsumer.preset);
    const first = firstConsumer.refresh();
    const second = secondConsumer.refresh();
    requests[1].request.resolve(response([9002]));
    await second;
    requests[0].request.resolve(response([9001]));
    await first;
    expect([...current().order_ids]).toEqual([9002]);
});
