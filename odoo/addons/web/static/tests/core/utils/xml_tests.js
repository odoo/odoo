/** @odoo-module **/
import { parseXML } from "@web/core/utils/xml";

QUnit.module("utils", () => {
    QUnit.module("xml");

    QUnit.test("parse error throws an exception", async (assert) => {
        assert.expect(3);

        let XMLToParse = "<invalid'>";
        try {
            parseXML(XMLToParse);
            assert.step("no error");
        } catch (e) {
            if (e.message.includes("error occured while parsing")) {
                assert.step("error");
            }
        }

        XMLToParse = "<div><div>Valid</div><div><Invalid</div></div>";
        try {
            parseXML(XMLToParse);
            assert.step("no error");
        } catch (e) {
            if (e.message.includes("error occured while parsing")) {
                assert.step("error");
            }
        }

        assert.verifySteps(["error", "error"]);
    });
});
