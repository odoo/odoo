import { expect, test } from "@odoo/hoot";

import { CardCompiler } from "@web/views/card/card_compiler";

function compileTemplate(arch) {
    const parser = new DOMParser();
    const xml = parser.parseFromString(arch, "text/xml");
    const compiler = new CardCompiler({ card: xml.documentElement });
    return compiler.compile("card");
}

test("card compiler keeps dynamic attributes on <main> and adds o_record_main", async () => {
    const arch = `
        <card>
            <templates>
                <t t-name="card">
                    <main t-att-class="{'test': true}">
                        <span>Content</span>
                    </main>
                </t>
            </templates>
        </card>`;
    const expected = `
        <t t-translation="off">
            <card>
                <templates>
                    <t t-name="card">
                        <div t-att-class="{'test': true}" class="o_record_main">
                            <span>Content</span>
                        </div>
                    </t>
                </templates>
            </card>
        </t>`;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});
