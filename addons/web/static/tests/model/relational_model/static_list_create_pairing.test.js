// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { makeLogger } from "@web/core/debug/debug_logger";
import { pairCreatedRows } from "@web/model/relational_model/static_list_utils";

describe.current.tags("headless");

/**
 * @param {string[]} virtualIds
 * @param {number[]} newIds
 * @returns {Map<string | number, number>}
 */
function pairedOrThrow(virtualIds, newIds) {
    const pairs = pairCreatedRows(virtualIds, newIds);
    if (!pairs) {
        throw new Error(
            `pairCreatedRows(${JSON.stringify(virtualIds)}, ${JSON.stringify(newIds)}) returned null`,
        );
    }
    return pairs;
}

describe("pairCreatedRows", () => {
    test("zips virtual ids against new ids in creation order", () => {
        const pairs = pairedOrThrow(["virtual_1", "virtual_2"], [11, 10]);

        expect(/** @type {Map<string, number>} */ (pairs).get("virtual_1")).toBe(10);
        expect(/** @type {Map<string, number>} */ (pairs).get("virtual_2")).toBe(11);
    });

    test("returns null when the counts disagree", () => {
        expect(pairCreatedRows(["virtual_1", "virtual_2"], [10])).toBe(null);
        expect(pairCreatedRows(["virtual_1"], [10, 11])).toBe(null);
    });

    test("an empty batch pairs nothing rather than failing", () => {
        const pairs = pairedOrThrow([], []);

        expect(pairs.size).toBe(0);
    });

    test("an unknown virtual id has no pairing", () => {
        const pairs = pairedOrThrow(["virtual_1"], [10]);

        expect(/** @type {Map<string, number>} */ (pairs).get("virtual_9")).toBe(
            undefined,
        );
    });

    test("ranking is numeric, not lexicographic", () => {
        const pairs = pairedOrThrow(["a", "b", "c"], [100, 9, 20]);

        expect([pairs.get("a"), pairs.get("b"), pairs.get("c")]).toEqual([9, 20, 100]);
    });
});

describe("pairCreatedRows positional identity", () => {
    test("a bottom create pairs when the new id sits where the row was", () => {
        const pairs = pairCreatedRows(["virtual_1"], [90], {
            clientIds: [2, 3, "virtual_1"],
            serverIds: [2, 3, 90],
        });

        expect(pairs).not.toBe(null);
        expect(/** @type {Map<string, number>} */ (pairs).get("virtual_1")).toBe(90);
    });

    test("a multi-row create pairs each row at its own position", () => {
        const pairs = pairCreatedRows(["virtual_1", "virtual_2"], [91, 90], {
            clientIds: [2, "virtual_1", "virtual_2"],
            serverIds: [2, 90, 91],
        });

        expect(pairs).not.toBe(null);
        expect(/** @type {Map<string, number>} */ (pairs).get("virtual_1")).toBe(90);
        expect(/** @type {Map<string, number>} */ (pairs).get("virtual_2")).toBe(91);
    });

    test("a foreign new id at a different position is refused", () => {
        const pairs = pairCreatedRows(["virtual_1"], [999], {
            clientIds: [2, "virtual_1", 3],
            serverIds: [2, 3, 999],
        });

        expect(pairs).toBe(null);
    });

    test("a virtual id absent from the client membership is refused", () => {
        const pairs = pairCreatedRows(["virtual_1"], [90], {
            clientIds: [2, 3],
            serverIds: [2, 3, 90],
        });

        expect(pairs).toBe(null);
    });

    test("without positions the rank-order zip is unchanged", () => {
        const pairs = pairedOrThrow(["virtual_1"], [999]);

        expect(/** @type {Map<string, number>} */ (pairs).get("virtual_1")).toBe(999);
    });
});

test("positions absent from both memberships do not establish identity", () => {
    const result = pairCreatedRows(["virtual_1"], [90], {
        clientIds: [2, 3],
        serverIds: [2, 3],
    });
    makeLogger("web.model.audit").logic("absent create positions", {
        paired: result !== null,
    });
    expect(result).toBe(null);
});

test("batch create position validation scans memberships once", () => {
    const virtualIds = Array.from({ length: 64 }, (_, i) => `virtual_${i}`);
    const newIds = Array.from({ length: 64 }, (_, i) => 100 + i);
    const existing = Array.from({ length: 64 }, (_, i) => i + 1);
    let reads = 0;
    const handler = {
        get(target, key, receiver) {
            if (typeof key === "string" && /^\d+$/.test(key)) {
                reads++;
            }
            return Reflect.get(target, key, receiver);
        },
    };
    const pairs = pairCreatedRows(virtualIds, [...newIds].reverse(), {
        clientIds: new Proxy([...existing, ...virtualIds], handler),
        serverIds: new Proxy([...existing, ...newIds], handler),
    });
    makeLogger("web.model.audit").logic("create membership lookup budget", {
        reads,
        pairs: pairs?.size,
    });
    expect(pairs && [...pairs]).toEqual(virtualIds.map((id, i) => [id, newIds[i]]));
    expect(reads).toBeLessThanOrEqual(256);
});

test("empty and prefix create batches do not scan unrelated membership tails", () => {
    const existing = Array.from({ length: 128 }, (_, i) => 1000 + i);
    for (const hasCreate of [false, true]) {
        let reads = 0;
        const handler = {
            get(target, key, receiver) {
                if (typeof key === "string" && /^\d+$/.test(key)) {
                    reads++;
                }
                return Reflect.get(target, key, receiver);
            },
        };
        const pairs = pairCreatedRows(
            hasCreate ? ["virtual_1"] : [],
            hasCreate ? [90] : [],
            {
                clientIds: new Proxy(
                    hasCreate ? ["virtual_1", ...existing] : existing,
                    handler,
                ),
                serverIds: new Proxy(hasCreate ? [90, ...existing] : existing, handler),
            },
        );
        makeLogger("web.model.audit").logic("create prefix lookup budget", {
            hasCreate,
            reads,
        });
        expect(pairs && [...pairs]).toEqual(hasCreate ? [["virtual_1", 90]] : []);
        expect(reads).toBe(hasCreate ? 2 : 0);
    }
});

test("unique membership permutations preserve the positional pairing contract", () => {
    const permutations = [
        [0, 1, 2],
        [0, 2, 1],
        [1, 0, 2],
        [1, 2, 0],
        [2, 0, 1],
        [2, 1, 0],
    ];
    let checked = 0;
    for (const left of permutations) {
        for (const right of permutations) {
            const clientIds = left.map((i) => [1, "v1", "v2"][i]);
            const serverIds = right.map((i) => [1, 10, 11][i]);
            const expected =
                clientIds.indexOf("v1") === serverIds.indexOf(10) &&
                clientIds.indexOf("v2") === serverIds.indexOf(11);
            const result = pairCreatedRows(["v1", "v2"], [11, 10], {
                clientIds,
                serverIds,
            });
            expect(result !== null).toBe(expected);
            checked++;
        }
    }
    makeLogger("web.model.audit").logic("create pairing permutation oracle", {
        checked,
    });
});
