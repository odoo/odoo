import { expect, test } from "@odoo/hoot";
import { htmlToXml } from "@l10n_it_pos/app/utils/html_to_xml";

const tags = ["aaBb", "aaBbCc"];

const attributes = ["xxYy", "xxYyZz"];

test("raw HTML to command XML", async () => {
    const html = `
        <aabb>
            <aabb xxyy="test"></aabb>
            <aabb xxyy="test"></aabb>
            <aabbcc xxyyzz="test"></aabbcc>
            <dd xxyyzz="test">
                <ee xxyy="test"></ee>
                <ff xxyy="test"></ff>
            </dd>
        </aabb>
    `;

    const actualXML = htmlToXml(html, tags, attributes);

    const expectedXML = `
        <aaBb>
            <aaBb xxYy="test" />
            <aaBb xxYy="test" />
            <aaBbCc xxYyZz="test" />
            <dd xxYyZz="test">
                <ee xxYy="test" />
                <ff xxYy="test" />
            </dd>
        </aaBb>
    `;

    expect(actualXML).toBe(expectedXML);
});
