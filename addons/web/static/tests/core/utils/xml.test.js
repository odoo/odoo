/** @odoo-module */

import { parseXML } from "@web/core/utils/xml";
import { expect, test } from "@odoo/hoot";

test("parse error throws an exception", () => {
    expect(() => parseXML("<invalid'>")).toThrow("error occured while parsing");
    expect(() => parseXML("<div><div>Valid</div><div><Invalid</div></div>")).toThrow(
        "error occured while parsing"
    );
});
