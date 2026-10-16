import { defineMailModels, start } from "@mail/../tests/mail_test_helpers";

import { describe, expect, test } from "@odoo/hoot";

import { getService, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop", "store_insert_mock_perf");
defineMailModels();

/**
 * Data shaped like a messaging menu page of `count` chats: each chat with its
 * two members, the other partner and the last message.
 */
function makeChatsData(count) {
    const data = {
        "discuss.channel": [],
        "discuss.channel.member": [],
        "res.partner": [],
    };
    for (let i = 1; i <= count; i++) {
        const channelId = 1000 + i;
        const partnerId = 1000 + i;
        const selfMemberId = 2 * i;
        const otherMemberId = 2 * i + 1;
        data["res.partner"].push({ id: partnerId, name: `Bench ${i}` });
        data["discuss.channel.member"].push(
            {
                id: selfMemberId,
                channel_id: channelId,
                partner_id: serverState.partnerId,
            },
            { id: otherMemberId, channel_id: channelId, partner_id: partnerId }
        );
        data["discuss.channel"].push({
            id: channelId,
            channel_type: "chat",
            channel_member_ids: [selfMemberId, otherMemberId],
            last_interest_dt: "2026-10-16 08:00:00",
            name: `Bench ${i}`,
            self_member_id: selfMemberId,
        });
    }
    return data;
}

const RUNS = 5;
const samples = {};

function median(values) {
    const sorted = [...values].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

async function measureInsert(count, run) {
    await start();
    const store = getService("mail.store");
    const data = makeChatsData(count);
    const startTime = performance.now();
    store.insert(data);
    const ms = performance.now() - startTime;
    (samples[count] ||= []).push(ms);
    expect(store["discuss.channel"].records.size).toBeGreaterThan(count - 1);
    if (run === RUNS) {
        const s = samples[count];
        console.log(
            `STORE_INSERT_MOCK_PERF chats=${count} runs=${s.length} ` +
                `median_ms=${median(s).toFixed(1)} min_ms=${Math.min(...s).toFixed(1)} ` +
                `max_ms=${Math.max(...s).toFixed(1)}`
        );
    }
}

for (const count of [50, 100]) {
    for (let run = 1; run <= RUNS; run++) {
        test.timeout(120000);
        test(`store insert mock perf: ${count} chats (run ${run}/${RUNS})`, async () =>
            measureInsert(count, run));
    }
}
