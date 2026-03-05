import { describe, expect, test } from "@odoo/hoot";
import { encodeTranslation, parseTranslatedText } from "../src/translation.patch";

describe.current.tags("headless");

test("encodeTranslation", () => {
    const metadata = ["web", "Component"];
    const translation = "Component";

    const encoded = encodeTranslation(0, metadata, translation);

    expect(encoded).toHaveLength(
        1 + // translated bit
            4 + // byte count
            JSON.stringify(metadata).length * 2 + // encoded metadata
            translation.length // translation
    );
    expect(encoded).toMatch(/Component$/);
});

test("parseTranslatedText", () => {
    expect(parseTranslatedText(encodeTranslation(0, ["web", "Component"], "Component"))).toEqual([
        "Component",
        [
            {
                context: "web",
                isTranslated: false,
                source: "Component",
                translation: "Component",
            },
        ],
    ]);
    expect(
        parseTranslatedText(/* xml */ `
            <span>\u200E${encodeTranslation(1, ["website", "Website", "Site Web"], "Site Web")}\u200E</span>
            <div>\u200D${encodeTranslation(0, ["web", "Menu"], "Menu")}</div>
        `)
    ).toEqual([
        /* xml */ `
            <span>\u200ESite Web\u200E</span>
            <div>\u200DMenu</div>
        `,
        [
            {
                context: "website",
                isTranslated: true,
                source: "Website",
                translation: "Site Web",
            },
            {
                context: "web",
                isTranslated: false,
                source: "Menu",
                translation: "Menu",
            },
        ],
    ]);
});
