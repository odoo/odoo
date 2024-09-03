/** @odoo-module */

import { describe, expect, mountOnFixture, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { parseUrl } from "../local_helpers";

describe(parseUrl(import.meta.url), () => {
    test("elementFromPoint and elementsFromPoint should be mocked", async () => {
        await mountOnFixture(/* xml */ `
            <div class="oui" style="position: absolute; left: 10px; top: 10px; width: 250px; height: 250px;">
                Oui
            </div>
        `);

        expect(".oui").toHaveRect({
            x: 10,
            y: 10,
            width: 250,
            height: 250,
        });

        const div = queryOne(".oui");
        expect(document.elementFromPoint(11, 11)).toBe(div);
        expect(document.elementsFromPoint(11, 11)).toEqual([
            div,
            document.body,
            document.documentElement,
        ]);

        expect(document.elementFromPoint(9, 9)).toBe(document.body);
        expect(document.elementsFromPoint(9, 9)).toEqual([document.body, document.documentElement]);
    });
});
