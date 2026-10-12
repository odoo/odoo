import { EMOJI_REGEX } from "@mail/utils/common/format";

import { expect, test } from "@odoo/hoot";

test.tags("headless");
test("EMOJI_REGEX correctly matches all types of emojis.", async () => {
    const testCases = [
        // Basic Emoji
        ["👺", "👺"],
        // Variation Selector-16
        ["☃\u{fe0f}", "☃️"],
        // Keycap Sequence
        ["1\u{fe0f}\u{20e3}", "1️⃣"],
        // Skin Tone Modifier
        ["🧔" + "🏾", "🧔🏾"],
        // ZWJ Sequence
        ["👨\u{200d}👩\u{200d}👧\u{200d}👦", "👨‍👩‍👧‍👦"],
        // Country Flag
        ["🇻" + "🇨", "🇻🇨"],
        // Subdivision Flag
        ["🏴\u{e0062}\u{e0065}\u{e0077}\u{e0061}\u{e006c}\u{e007f}", "🏴󠁢󠁥󠁷󠁡󠁬󠁿"],
        // Overqualified Emoji
        ["⛄\u{fe0f}", "⛄️"],
    ];
    for (const [testCase, expected] of testCases) {
        const match = testCase.match(EMOJI_REGEX);
        expect(match).toHaveLength(1);
        expect(match[0]).toBe(expected);
    }
});
