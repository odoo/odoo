/** @odoo-module */

import { expect, test } from "@odoo/hoot";

import { parseXML } from "@web/core/utils/xml";

test.tags("headless")("parse error throws an exception", () => {
    expect(() => parseXML("<invalid'>")).toThrow("error occured while parsing");
    expect(() => parseXML("<div><div>Valid</div><div><Invalid</div></div>")).toThrow(
        "error occured while parsing"
    );
});
