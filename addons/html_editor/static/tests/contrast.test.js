import { describe, expect, test } from "@odoo/hoot";
import { ContrastPlugin, adjustColorContrast } from "@html_editor/main/font/contrast_plugin";
import { testEditor } from "./_helpers/editor";
import { setColor } from "./_helpers/user_actions";
import { unformat } from "./_helpers/format";

const lightModeTests = [
    {
        name: "pure white on white, darken",
        input: {
            color: "rgb(255, 255, 255)",
            background: "rgb(255, 255, 255)",
        },
        expected: "rgb(183, 183, 183)",
    },
    {
        name: "very light gray on white, darken",
        input: {
            color: "rgb(240, 240, 240)",
            background: "rgb(255, 255, 255)",
        },
        expected: "rgb(183, 183, 183)",
    },
    {
        name: "light blue on very light bg, darken",
        input: {
            color: "rgb(200, 220, 255)",
            background: "rgb(250, 250, 250)",
        },
        expected: "rgb(137, 180, 255)",
    },
    {
        name: "light pastel green on white, darken",
        input: {
            color: "rgb(210, 240, 210)",
            background: "rgb(255, 255, 255)",
        },
        expected: "rgb(103, 204, 103)",
    },
    {
        name: "very dark red on light background, no change",
        input: {
            color: "rgb(21, 4, 14)",
            background: "rgb(255, 255, 255)",
        },
        expected: undefined,
    },
    {
        name: "dark blue on white, no change",
        input: {
            color: "rgb(0, 50, 100)",
            background: "rgb(255, 255, 255)",
        },
        expected: undefined,
    },
    {
        name: "very light pink on white, darken",
        input: {
            color: "rgb(255, 200, 220)",
            background: "rgb(255, 255, 255)",
        },
        expected: "rgb(255, 152, 190)",
    },
    {
        name: "very light yellow on white, darken",
        input: {
            color: "rgb(255, 239, 198)",
            background: "rgb(255, 255, 255)",
        },
        expected: "rgb(238, 171, 0)",
    },
    {
        name: "medium green on light background, no change",
        input: {
            color: "rgb(100, 150, 80)",
            background: "rgb(255, 255, 255)",
        },
        expected: undefined,
    },
    {
        name: "black on white, no change",
        input: {
            color: "rgb(0, 0, 0)",
            background: "rgb(255, 255, 255)",
        },
        expected: undefined,
    },
    {
        name: "strong blue on white, no change",
        input: {
            color: "rgb(0, 0, 255)",
            background: "rgb(255, 255, 255)",
        },
        expected: undefined,
    },
    {
        name: "invalid fg, undefined",
        input: {
            color: "invalid",
            background: "rgb(255, 255, 255)",
        },
        expected: undefined,
    },
    {
        name: "invalid bg, undefined",
        input: {
            color: "rgb(0, 0, 0)",
            background: "invalid",
        },
        expected: undefined,
    },
];

const darkModeTests = [
    {
        name: "very dark red on dark background, lighten",
        input: {
            color: "rgb(21, 4, 4)",
            background: "rgb(38, 42, 54)",
        },
        expected: "rgb(170, 32, 32)",
    },
    {
        name: "dark blue on dark background, lighten",
        input: {
            color: "rgb(0, 50, 100)",
            background: "rgb(38, 42, 54)",
        },
        expected: "rgb(0, 86, 173)",
    },
    {
        name: "medium orange on dark background, no change",
        input: {
            color: "rgb(200, 120, 50)",
            background: "rgb(38, 42, 54)",
        },
        expected: undefined,
    },
    {
        name: "pure black on black, lighten",
        input: {
            color: "rgb(0, 0, 0)",
            background: "rgb(0, 0, 0)",
        },
        expected: "rgb(64, 64, 64)",
    },
    {
        name: "very dark gray on dark bg, lighten",
        input: {
            color: "rgb(20, 20, 20)",
            background: "rgb(38, 42, 54)",
        },
        expected: "rgb(88, 88, 88)",
    },
    {
        name: "dark purple on dark bg, lighten",
        input: {
            color: "rgb(40, 0, 60)",
            background: "rgb(38, 42, 54)",
        },
        expected: "rgb(137, 0, 205)",
    },
    {
        name: "white on black, no change",
        input: {
            color: "rgb(255, 255, 255)",
            background: "rgb(0, 0, 0)",
        },
        expected: undefined,
    },
    {
        name: "bright yellow on black, no change",
        input: {
            color: "rgb(255, 255, 0)",
            background: "rgb(0, 0, 0)",
        },
        expected: undefined,
    },
];

function testContrast(cases) {
    for (const { name, input, expected } of cases) {
        test(name, () => {
            const result = adjustColorContrast(input.color, input.background);
            expect(result).toBe(expected);
        });
    }
}

describe("Light background", () => {
    testContrast(lightModeTests);
});

describe("Dark background", () => {
    testContrast(darkModeTests);
});

test("should not restore manually applied colors while restoring other original colors on save", async () => {
    await testEditor({
        contentBefore: '<p>abc<font style="color: rgb(255, 255, 255)">d[e]f</font></p>',
        contentBeforeEdit:
            '<p>abc<font style="color: rgb(183, 183, 183);" data-original-color="rgb(255, 255, 255)">d[e]f</font></p>',
        stepFunction: setColor("rgb(255, 255, 255)", "color"),
        contentAfterEdit: unformat(`
            <p>abc
                <font style="color: rgb(183, 183, 183);" data-original-color="rgb(255, 255, 255)">d</font>
                <font style="color: rgb(255, 255, 255);">[e]</font>
                <font style="color: rgb(183, 183, 183);" data-original-color="rgb(255, 255, 255)">f</font>
            </p>
        `),
        contentAfter: unformat(`
            <p>abc
                <font style="color: rgb(255, 255, 255);">d</font>
                <font style="color: rgb(255, 255, 255);">[e]</font>
                <font style="color: rgb(255, 255, 255);">f</font>
            </p>
        `),
        config: { includePlugins: [ContrastPlugin] },
    });
});

test("should apply contrast to color classes with important style and remove it on manual color change", async () => {
    await testEditor({
        contentBefore: '<p>abc<font class="text-o-color-3">[def]</font></p>',
        contentBeforeEdit:
            '<p>abc<font class="text-o-color-3" data-original-color="" style="color: rgb(190, 182, 175) !important;">[def]</font></p>',
        stepFunction: setColor("rgb(190, 182, 175)", "color"),
        contentAfterEdit: unformat(`
            <p>abc<font class="" style="color: rgb(190, 182, 175);">[def]</font></p>
        `),
        contentAfter: unformat(`
            <p>abc<font style="color: rgb(190, 182, 175);">[def]</font></p>
        `),
        config: { includePlugins: [ContrastPlugin] },
    });
});

test("should use background color classes for contrast and remove temporary important style on save", async () => {
    await testEditor({
        contentBefore:
            '<p><font class="bg-o-color-5">abc<font class="text-o-color-5">[def]</font></font></p>',
        contentBeforeEdit: unformat(`
            <p>
                <font class="bg-o-color-5">abc
                    <font class="text-o-color-5" data-original-color="" style="color: rgb(91, 64, 85) !important;">[def]</font>
                </font>
            </p>
        `),
        contentAfter: unformat(`
            <p><font class="bg-o-color-5">abc<font class="text-o-color-5">[def]</font></font></p>
        `),
        config: { includePlugins: [ContrastPlugin] },
    });
});
