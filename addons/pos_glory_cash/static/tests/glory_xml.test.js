import { describe, expect, test } from "@odoo/hoot";
import { makeGloryHeader, parseGloryXml, serializeGloryXml } from "@pos_glory_cash/utils/glory_xml";

const TEST_XML = '<MockElement mockattribute="mock value">Mock Content</MockElement>';
const TEST_XML_WITH_CHILD = "<MockElement><ChildElement>Child Content</ChildElement></MockElement>";
const TEST_XML_WITH_CONTROL_CHARS = `\x04${TEST_XML}\0`;

describe("parse glory xml", () => {
    test("parses simple XML correctly", async () => {
        const result = await parseGloryXml(new Blob([TEST_XML]));

        expect(result).toBeInstanceOf(Element);
        expect(result.tagName).toBe("MockElement");
        expect(result.textContent).toBe("Mock Content");
        expect(result.getAttribute("mockattribute")).toBe("mock value");
    });

    test("parses simple XML with control characters correctly", async () => {
        const result = await parseGloryXml(new Blob([TEST_XML_WITH_CONTROL_CHARS]));

        expect(result).toBeInstanceOf(Element);
        expect(result.tagName).toBe("MockElement");
        expect(result.textContent).toBe("Mock Content");
        expect(result.getAttribute("mockattribute")).toBe("mock value");
    });
});

describe("serialize glory xml", () => {
    test("serializes a simple element correctly", () => {
        const result = serializeGloryXml({
            name: "MockElement",
            attributes: { mockattribute: "mock value" },
            children: ["Mock Content"],
        });

        expect(result).toBe(`${TEST_XML}\0`);
    });

    test("serializes an element with children correctly", () => {
        const result = serializeGloryXml({
            name: "MockElement",
            children: [
                {
                    name: "ChildElement",
                    children: ["Child Content"],
                },
            ],
        });

        expect(result).toBe(`${TEST_XML_WITH_CHILD}\0`);
    });
});

describe("make glory header", () => {
    test("sets the ID to 'OdooPos'", () => {
        const result = makeGloryHeader(1);

        expect(result[0].name).toBe("Id");
        expect(result[0].children[0]).toBe("OdooPos");
    });

    test("sets the sequence number to the provided number", () => {
        const result = makeGloryHeader(1);

        expect(result[1].name).toBe("SeqNo");
        expect(parseInt(result[1].children[0])).toBe(1);
    });

    test("pads the sequence number to 11 characters", () => {
        const result = makeGloryHeader(1);

        expect(result[1].name).toBe("SeqNo");
        expect(result[1].children[0]).toBe("00000000001");
    });

    test("sets the session ID to the provided value", () => {
        const result = makeGloryHeader(1, "mockSessionId");

        expect(result[2].name).toBe("SessionID");
        expect(result[2].children[0]).toBe("mockSessionId");
    });

    test("does not include the session ID if it is empty", () => {
        const result = makeGloryHeader(1, "");

        expect(result).toHaveLength(2);
    });
});
