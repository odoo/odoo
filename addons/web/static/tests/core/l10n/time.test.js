import { beforeEach, describe, expect, test } from "@odoo/hoot";
import {
    patchWithCleanup,
    defineParams,
} from "@web/../tests/web_test_helpers";
import { localization } from "@web/core/l10n/localization";
import { parseTime } from "@web/core/l10n/time";

const { Settings } = luxon;

defineParams({
    lang_parameters: {
        time_format: "%H:%M:%S",
    },
});

beforeEach(() => {
    patchWithCleanup(localization, {
        timeFormat: "%H:%M:%S",
    });
});

describe.current.tags("headless");
test("parseTime (various entries)", async () => {

    const testSet = [
        // Default ":" separator
        ["8:15", "8:15:00"],
        ["15:15", "15:15:00"],
        ["15:5", "15:50:00"],
        ["15:15:34", "15:15:34"],
        ["24:00", "0:00:00"],
        ["10:", "10:00:00"],

        // No separators
        ["123", "12:30:00"],
        ["101", "10:10:00"],
        ["1015", "10:15:00"],
        ["101534", "10:15:34"],
        ["10  15", "10:15:00"],
        ["10  15   34", "10:15:34"],
        ["1 15", "1:15:00"],
        ["35", "3:50:00"],

        // Other separators
        ["10h", "10:00:00"],
        ["1h30", "1:30:00"],
        ["10h15", "10:15:00"],
        ["10h15:34", "10:15:34"],

        // Am / Pm
        ["8pm", "20:00:00"],
        ["8PM", "20:00:00"],
        ["8 pm", "20:00:00"],
        ["8:55pm", "20:55:00"],
        ["8:55 pm", "20:55:00"],
        ["8:55pm 33", "20:55:33"],
        ["8:55:33pm", "20:55:33"],

        ["12am", "0:00:00"],
        ["12pm", "12:00:00"],
        ["8ppp", null],

        // Wrong inputs
        ["28:00", null],
        ["28:", null],
        ["abc", null],
        ["10101010", null],
        ["+10", null],
        ["-10", null],
        ["|[{,;:10", null],
    ];

    for (const [input, expected] of testSet) {
        let result = parseTime(input, true);
        if (result) {
            result = result.toString(true);
        }
        expect(result).toBe(expected, {
            message: `"${input}" should parse to "${expected}" and got "${result}"`,
        });
    }
});

describe.current.tags("headless");
test("parseTime (no seconds)", async () => {

    const testSet = [
        ["8:15", "8:15"],
        ["10:15", "10:15"],
        ["10:5", "10:50"],
        ["24:00", "0:00"],
        ["10:", "10:00"],
        ["101", "10:10"],
        ["350", "3:50"],
        ["1015", "10:15"],
        ["10  15", "10:15"],
        ["1 15", "1:15"],

        ["8:55aaa", null],
        ["8:55:33", null],
        ["8:55:", null],
        ["08553", null],
        ["085533", null],
        ["08553300", null],
        ["8:55:33pm", null],
    ];

    for (const [input, expected] of testSet) {
        let result = parseTime(input, false);
        if (result) {
            result = result.toString(false);
        }
        expect(result).toBe(expected, {
            message: `(parseSeconds=false) "${input}" should parse to "${expected}" and got "${result}"`,
        });
    }
});

describe.current.tags("headless");
test("parseTime (arabic numbers)", async () => {
    patchWithCleanup(Settings, { defaultNumberingSystem: "arab" });

    const testSet = [
        ["11", "١١:٠٠"],
        ["11:45", "١١:٤٥"],
        ["١١", "١١:٠٠"],
        ["١١:٤٥", "١١:٤٥"],
    ];

    for (const [input, expected] of testSet) {
        const result = parseTime(input).toString(false);
        expect(result).toBe(expected, {
            message: `"${input}" should parse to "${expected}" and got "${result}"`,
        });
    }
});
