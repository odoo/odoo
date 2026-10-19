import { test, expect } from "@odoo/hoot";
import { applyInheritance } from "@web/core/template_inheritance";
import { patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

const parser = new DOMParser();
const serializer = new XMLSerializer();

function _applyInheritance(arch, inherits, url = "test/from_op") {
    const archXmlDoc = parser.parseFromString(arch, "text/xml");
    const inheritsDoc = parser.parseFromString(inherits, "text/xml");
    archXmlDoc.documentElement.setAttribute("t-translation-context", "from_target");
    const modifiedTemplate = applyInheritance(
        archXmlDoc.documentElement,
        inheritsDoc.documentElement,
        url
    );
    return serializer.serializeToString(modifiedTemplate);
}

test("warn when contains(@class, ...)", async () => {
    serverState.debug = "1";
    patchWithCleanup(console, {
        warn(msg) {
            expect.step(msg);
        },
    });
    const arch = `<t t-name="web.A"><div class="my-class" /></t>`;
    const operations = `
    <t t-inherit="web.A"><xpath expr="*[contains(@class, 'my-class')]" position="inside"><span/></xpath></t>`;
    expect(_applyInheritance(arch, operations, "")).toBe(
        `<t t-name="web.A" t-translation-context="from_target"><div class="my-class"><span t-translation-context=""/></div></t>`
    );
    expect.verifySteps([
        `Error-prone use of @class in template "web.A" (or one of its inheritors). Use the hasclass(*classes) function to filter elements by their classes`,
    ]);
});

test("no operation", async () => {
    const arch = `<t t-name="web.A" t-translation-context="from_target"> <div><h2>Title</h2>text</div> </t>`;
    const operations = `<t/>`;
    expect(_applyInheritance(arch, operations)).toBe(arch);
});

test("single operation: replace", async () => {
    const toTest = [
        {
            arch: `<t t-name="web.A"> <div><h2>Title</h2>text</div> </t>`,
            operations: `
                <t>
                    <xpath expr="./div/h2" position="replace"><h3>Other title</h3></xpath>
                </t>`,
            result: `<t t-name="web.A" t-translation-context="from_target"> <div><h3 t-translation-context="from_op">Other title</h3>text</div> </t>`,
            // TODO check if text should be there? (I think there is a bug in python code)
        },
    ];
    for (const { arch, operations, result } of toTest) {
        expect(_applyInheritance(arch, operations)).toBe(result);
    }
});

test("single operation: replace (debug mode)", async () => {
    serverState.debug = "1";
    const toTest = [
        {
            arch: `<t t-name="web.A"> <div><h2>Title</h2>text</div> </t>`,
            operations: `
                <t>
                    <xpath expr="./div/h2" position="replace"><h3>Other title</h3></xpath>
                </t>`,
            result: `<t t-name="web.A" t-translation-context="from_target"> <div><!-- From file: test/from_op ; expr="./div/h2" ; position="replace" --><h3 t-translation-context="from_op">Other title</h3>text</div> </t>`,
        },
    ];
    for (const { arch, operations, result } of toTest) {
        expect(_applyInheritance(arch, operations)).toBe(result);
    }
});

test("single operation: replace root (and use a $0)", async () => {
    const toTest = [
        {
            arch: `<t t-name="web.A"> <div>I was petrified</div> </t>`,
            operations: `
                <t>
                    <xpath expr="." position="replace"><div>At first I was afraid</div>$0</xpath>
                </t>`,
            result: `<div t-translation-context="from_op" t-name="web.A">At first I was afraid</div>`,
            // in outer mode with no parent only first child of operation is kept
        },
        {
            arch: `<t t-name="web.A"> <div>I was petrified</div> </t>`,
            operations: `
                <t>
                    <xpath expr="." position="replace"> <div>$0</div><div>At first I was afraid</div> </xpath>
                </t>`,
            result: `<div t-translation-context="from_op" t-name="web.A"><t t-name="web.A" t-translation-context="from_target"> <div>I was petrified</div> </t></div>`,
        },
        {
            arch: `<t t-name="web.A"> <div>I was petrified</div> </t>`,
            operations: `
                <t>
                    <xpath expr="." position="replace"> <t><t t-if="cond"><div>At first I was afraid</div></t><t t-else="">$0</t></t> </xpath>
                </t>`,
            result: `<t t-translation-context="from_op" t-name="web.A"><t t-if="cond"><div>At first I was afraid</div></t><t t-else=""><t t-name="web.A" t-translation-context="from_target"> <div>I was petrified</div> </t></t></t>`,
        },
        {
            arch: `<form t-name="template_1_1" random-attr="gloria"> <div>At first I was afraid</div> <form>Inner Form</form> </form>`,
            operations: `
                <t>
                    <xpath expr="//form" position="replace">
                        <div> Form replacer </div>
                    </xpath>
                </t>`,
            result: `<div t-translation-context="from_op" t-name="template_1_1"> Form replacer </div>`,
        },
        {
            arch: `<form t-name="template_1_1" random-attr="gloria"> <div>At first I was afraid</div> </form>`,
            operations: `
                <t t-name="template_1_2">
                    <xpath expr="." position="replace">
                        <div overriden-attr="overriden">And I grew strong</div>
                    </xpath>
                </t>
            `,
            result: `<div overriden-attr="overriden" t-translation-context="from_op" t-name="template_1_1">And I grew strong</div>`,
        },
    ];
    for (const { arch, operations, result } of toTest) {
        expect(_applyInheritance(arch, operations)).toBe(result);
    }
});

test("single operation: replace (mode inner)", async () => {
    const toTest = [
        {
            arch: `<t t-name="web.A"> <div> A <span/> B <span/> C </div> </t>`,
            operations: `
                <t>
                    <xpath expr="./div" position="replace" mode="inner"> E <div/> F <span attr1="12"/> </xpath>
                </t>`,
            result: `<t t-name="web.A" t-translation-context="from_target"> <div> E <div t-translation-context="from_op"/> F <span attr1="12" t-translation-context="from_op"/> </div> </t>`,
        },
    ];
    for (const { arch, operations, result } of toTest) {
        expect(_applyInheritance(arch, operations)).toBe(result);
    }
});

test("single operation: replace (mode inner) (debug mode)", async () => {
    serverState.debug = "1";
    const toTest = [
        {
            arch: `<t t-name="web.A"> <div> A <span/> B <span/> C </div> </t>`,
            operations: `
                <t>
                    <xpath expr="./div" position="replace" mode="inner"> E <div/> F <span attr1="12"/> </xpath>
                </t>`,
            result: `<t t-name="web.A" t-translation-context="from_target"> <div><!-- From file: test/from_op ; expr="./div" ; position="replace" ; mode="inner" --> E <div t-translation-context="from_op"/> F <span attr1="12" t-translation-context="from_op"/> </div> </t>`,
        },
    ];
    for (const { arch, operations, result } of toTest) {
        expect(_applyInheritance(arch, operations)).toBe(result);
    }
});

test("single operation: before", async () => {
    const toTest = [
        {
            arch: `<t t-name="web.A"> <div>AAB is the best<h2>Title</h2>text</div> </t>`,
            operations: `
                <t>
                    <xpath expr="./div/h2" position="before"> <h3>Other title</h3>Yooplahoo!<h4>Yet another title</h4> </xpath>
                </t>`,
            result: `<t t-name="web.A" t-translation-context="from_target"> <div>AAB is the best <h3 t-translation-context="from_op">Other title</h3>Yooplahoo!<h4 t-translation-context="from_op">Yet another title</h4> <h2>Title</h2>text</div> </t>`,
        },
        {
            arch: `<t t-name="web.A"> <div>AAB is the best<h2>Title</h2><div><span>Ola</span></div></div> </t>`,
            operations: `
                <t>
                    <xpath expr="./div/h2" position="before"> <xpath expr="./div/div/span" position="move" /> </xpath>
                </t>`,
            result: `<t t-name="web.A" t-translation-context="from_target"> <div>AAB is the best <span t-translation-context="from_target">Ola</span> <h2>Title</h2><div/></div> </t>`,
        },
        {
            arch: `<t t-name="web.A"> a <div/> </t>`,
            operations: `
                <t>
                    <xpath expr="./div" position="before"> 4 </xpath>
                </t>`,
            result: `<t t-name="web.A" t-translation-context="from_target"> a 4 <div/> </t>`,
        },
    ];
    for (const { arch, operations, result } of toTest) {
        expect(_applyInheritance(arch, operations)).toBe(result);
    }
});

test("single operation: inside", async () => {
    const toTest = [
        {
            arch: `<t t-name="web.A" t-translation-context="from_target"> <div>AAB is the best <h2>Title</h2> <div/> </div> </t>`,
            operations: `
                <t>
                    <xpath expr="./div/div" position="inside"> Hop! <xpath expr="./div/h2" position="move" /> <span>Yellow</span> </xpath>
                </t>`,
            result: `<t t-name="web.A" t-translation-context="from_target"> <div>AAB is the best <div> Hop! <h2 t-translation-context="from_target">Title</h2> <span t-translation-context="from_op">Yellow</span> </div> </div> </t>`,
        },
        {
            arch: `<t><div/></t>`,
            operations: `
                <t>
                    <xpath expr="./div" position="inside">4</xpath>
                </t>`,
            result: `<t t-translation-context="from_target"><div>4</div></t>`,
        },
        {
            arch: `<t><div>\na \n </div></t>`,
            operations: `
                <t>
                    <xpath expr="./div" position="inside">4</xpath>
                </t>`,
            result: `<t t-translation-context="from_target"><div>\na4</div></t>`,
        },
        {
            arch: `<t>a<div></div><span/></t>`,
            operations: `
                <t>
                    <xpath expr="./div" position="inside"><span/></xpath>
                </t>`,
            result: `<t t-translation-context="from_target">a<div><span t-translation-context="from_op"/></div><span/></t>`,
        },
    ];
    for (const { arch, operations, result } of toTest) {
        expect(_applyInheritance(arch, operations)).toBe(result);
    }
});

test("single operation: after", async () => {
    const toTest = [
        {
            arch: `<t t-name="web.A" t-translation-context="from_target"> <div> AAB is the best <h2>Title</h2> <div id="1"/> <div id="2"/> </div> </t>`,
            operations: `
                <t>
                    <xpath expr="./div/h2" position="after"> Hop! <xpath expr="./div/div[@id=2]" position="move" /> <span>Yellow</span> </xpath>
                </t>`,
            result: `<t t-name="web.A" t-translation-context="from_target"> <div> AAB is the best <h2>Title</h2> Hop! <div id="2" t-translation-context="from_target"/> <span t-translation-context="from_op">Yellow</span>  <div id="1"/>  </div> </t>`,
        },
        {
            arch: `<t t-name="web.A" t-translation-context="from_target"> <div/>a </t>`,
            operations: `
                <t>
                    <xpath expr="./div" position="after">4</xpath>
                </t>`,
            result: `<t t-name="web.A" t-translation-context="from_target"> <div/>4a </t>`,
        },
    ];
    for (const { arch, operations, result } of toTest) {
        expect(_applyInheritance(arch, operations)).toBe(result);
    }
});

test("single operation: attributes", async (assert) => {
    const toTest = [
        {
            arch: `<t t-name="web.A"> <div attr1="12" attr2="a b" attr3="to remove" /> </t>`,
            operations: `
                <t>
                    <xpath expr="./div" position="attributes">
                        <attribute name="attr1">45</attribute>
                        <attribute name="attr3"></attribute>
                        <attribute name="attr2" add="c" separator=" "></attribute>
                        <attribute name="attr2" remove="a" separator=" "></attribute>
                        <attribute name="attr4">new</attribute>
                    </xpath>
                </t>`,
            result: `<t t-name="web.A" t-translation-context="from_target"> <div attr1="45" attr2="b c" t-translation-context-attr1="from_op" attr4="new" t-translation-context-attr4="from_op"/> </t>`,
        },
        {
            arch: `<t t-name="web.A"> <div><a href="1"/><div><a href="2"/></div></div> </t>`,
            operations: `
                <t>
                    <xpath expr="//a[@href='2']" position="attributes">
                        <attribute name="found">1</attribute>
                    </xpath>
                </t>`,
            result: `<t t-name="web.A" t-translation-context="from_target"> <div><a href="1"/><div><a href="2" found="1" t-translation-context-found="from_op"/></div></div> </t>`,
        },
    ];
    for (const { arch, operations, result } of toTest) {
        expect(_applyInheritance(arch, operations)).toBe(result);
    }
});

test("single operation: attributes (debug mode)", async () => {
    serverState.debug = "1";
    const toTest = [
        {
            arch: `<t t-name="web.A"> <div attr1="12" attr2="a b" attr3="to remove" /> </t>`,
            operations: `
                <t>
                    <xpath expr="./div" position="attributes">
                        <attribute name="attr1">45</attribute>
                        <attribute name="attr3"></attribute>
                        <attribute name="attr2" add="c" separator=" "></attribute>
                        <attribute name="attr2" remove="a" separator=" "></attribute>
                        <attribute name="attr4">new</attribute>
                    </xpath>
                </t>`,
            result: `<t t-name="web.A" t-translation-context="from_target"> <!-- From file: test/from_op ; expr="./div" ; position="attributes" --><div attr1="45" attr2="b c" t-translation-context-attr1="from_op" attr4="new" t-translation-context-attr4="from_op"/> </t>`,
        },
    ];
    for (const { arch, operations, result } of toTest) {
        expect(_applyInheritance(arch, operations)).toBe(result);
    }
});

test("xpath with hasclass", async () => {
    const toTest = [
        {
            arch: `<t><div class="abc"/></t>`,
            operations: `<t><xpath expr="./div[hasclass('abc')]" position="replace"></xpath></t>`,
            result: `<t t-translation-context="from_target"/>`,
        },
        {
            arch: `<t><div class="abc "/></t>`,
            operations: `<t><xpath expr="./div[hasclass('abc')]" position="replace"></xpath></t>`,
            result: `<t t-translation-context="from_target"/>`,
        },
        {
            arch: `<t><div class=" abc"/></t>`,
            operations: `<t><xpath expr="./div[hasclass('abc')]" position="replace"></xpath></t>`,
            result: `<t t-translation-context="from_target"/>`,
        },
        {
            arch: `<t><div class=" abc "/></t>`,
            operations: `<t><xpath expr="./div[hasclass('abc')]" position="replace"></xpath></t>`,
            result: `<t t-translation-context="from_target"/>`,
        },
        {
            arch: `<t><div class="d abc e"/></t>`,
            operations: `<t><xpath expr="./div[hasclass('abc')]" position="replace"></xpath></t>`,
            result: `<t t-translation-context="from_target"/>`,
        },
        {
            arch: `<t><div class="d abc"/></t>`,
            operations: `<t><xpath expr="./div[hasclass('abc')]" position="replace"></xpath></t>`,
            result: `<t t-translation-context="from_target"/>`,
        },
        {
            arch: `<t><div class="abc d"/></t>`,
            operations: `<t><xpath expr="./div[hasclass('abc')]" position="replace"></xpath></t>`,
            result: `<t t-translation-context="from_target"/>`,
        },
        {
            arch: `<t><div class="abcd e abc"/></t>`,
            operations: `<t><xpath expr="./div[hasclass('abc')]" position="replace"></xpath></t>`,
            result: `<t t-translation-context="from_target"/>`,
        },
        {
            arch: `<t><div class="abcd e abc"/></t>`,
            operations: `<t><xpath expr="./div[hasclass('abc', 'abcd' )]" position="replace"></xpath></t>`,
            result: `<t t-translation-context="from_target"/>`,
        },
        {
            arch: `<t><div class="abcd e abc"/></t>`,
            operations: `<t><xpath expr="./div[hasclass('abc') and hasclass('abcd')]" position="replace"></xpath></t>`,
            result: `<t t-translation-context="from_target"/>`,
        },
        {
            arch: `<t><div class="abcd"/></t>`,
            operations: `<t><xpath expr="./div[hasclass('abc')]" position="replace"></xpath></t>`,
            isError: true,
        },
        {
            arch: `<t><div class="dabc"/></t>`,
            operations: `<t><xpath expr="./div[hasclass('abc')]" position="replace"></xpath></t>`,
            isError: true,
        },
        {
            arch: `<t><div class="dabc"/></t>`,
            operations: `<t><xpath expr="./div[ends-with(@class, 'bc')]" position="replace"></xpath></t>`,
            isError: true,
        },
    ];
    for (const { arch, operations, result, isError } of toTest) {
        if (isError) {
            expect(() => _applyInheritance(arch, operations)).toThrow();
        } else {
            expect(_applyInheritance(arch, operations)).toBe(result);
        }
    }
});
