import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { Component, t, useProps, xml } from "@odoo/owl";
import { defineModels, fields, models, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { parseXML } from "@web/core/utils/xml";
import { CardPopover } from "@web/views/card/card_popover/card_popover";

class Partner extends models.Model {
    display_name = fields.Char();
    email = fields.Char();

    _records = [{ id: 1, display_name: "Jean Michel", email: "jean@example.com" }];

    _views = {
        "card,1": /* xml */ `
            <card>
                <templates>
                    <t t-name="card">
                        <div class="o_custom_card_body">
                            <field name="email"/>
                        </div>
                    </t>
                </templates>
            </card>
        `,
    };
}

defineModels([Partner]);

/**
 * Mounts a real `CardPopover`, wrapped in a small component that provides
 * the `footer` slot and forwards well-chosen props.
 */
async function mountCardPopover(props = {}) {
    const cardPopoverProps = {
        close: () => {},
        resModel: "partner",
        fields: Partner._fields,
        resId: 1,
        getDefaultPopoverBody: () => parseXML(`<t t-name="card"><span class="default-body"/></t>`),
        ...props,
    };
    class Parent extends Component {
        static components = { CardPopover };
        props = useProps({
            cardPopoverProps: t.any(),
        });
        static template = xml`
            <CardPopover t-props="this.props.cardPopoverProps">
                <t t-set-slot="footer">
                    <button class="test-footer-btn">
                        Footer
                    </button>
                </t>
            </CardPopover>
        `;
    }
    await mountWithCleanup(Parent, { props: { cardPopoverProps } });
}

test("with default header, body and footer (no popoverNode)", async () => {
    await mountCardPopover();
    expect(`.o_popover_header`).toHaveText("Jean Michel");
    expect(`.o_popover_body .default-body`).toHaveCount(1);
    expect(`.o_popover_footer .test-footer-btn`).toHaveCount(1);
});

test("with popoverNode with card_id attribute", async () => {
    await mountCardPopover({
        popoverNode: parseXML(`<popover card_id="1"/>`),
    });
    expect(`.o_popover_body .o_custom_card_body`).toHaveCount(1);
    expect(`.o_popover_body`).toHaveText("jean@example.com");
});

test("with popoverNode defining only the body", async () => {
    await mountCardPopover({
        popoverNode: parseXML(`
            <popover>
                <templates>
                    <t t-name="popover-body">
                        <span class="custom-body">Custom Body</span>
                        <div class="email"><field name="email"/></div>
                    </t>
                </templates>
            </popover>
        `),
    });
    expect(`.o_popover_header`).toHaveCount(0);
    expect(`.o_popover_body .custom-body`).toHaveText("Custom Body");
    expect(`.o_popover_body .email`).toHaveText("jean@example.com");
    expect(`.o_popover_footer .test-footer-btn`).toHaveCount(1);
});

test("with popoverNode defining only the header", async () => {
    await mountCardPopover({
        popoverNode: parseXML(`
            <popover>
                <templates>
                    <t t-name="popover-header">
                        <span class="custom-header">Custom Header</span>
                    </t>
                </templates>
            </popover>
        `),
    });
    expect(`.o_popover_header .custom-header`).toHaveText("Custom Header");
    expect(`.o_popover_body .default-body`).toHaveCount(1);
    expect(`.o_popover_footer .test-footer-btn`).toHaveCount(1);
});

test("with popoverNode defining only the footer", async () => {
    await mountCardPopover({
        popoverNode: parseXML(`
            <popover>
                <templates>
                    <t t-name="popover-footer">
                        <button class="custom-footer-btn">Custom</button>
                    </t>
                </templates>
            </popover>
        `),
    });
    expect(`.o_popover_header`).toHaveText("Jean Michel");
    expect(`.o_popover_body .default-body`).toHaveCount(1);
    expect(`.o_popover_footer .test-footer-btn`).toHaveCount(0);
    expect(`.o_popover_footer .custom-footer-btn`).toHaveCount(1);
});

test(`with popoverNode defining a footer with replace="O"`, async () => {
    await mountCardPopover({
        popoverNode: parseXML(`
            <popover>
                <templates>
                    <t t-name="popover-footer" replace="0">
                        <button class="custom-footer-btn">Custom</button>
                    </t>
                </templates>
            </popover>
        `),
    });
    expect(`.o_popover_footer .test-footer-btn`).toHaveCount(1);
    expect(`.o_popover_footer .custom-footer-btn`).toHaveCount(1);
});

test("click on the close cross", async () => {
    await mountCardPopover({ close: () => expect.step("close") });
    await click(`.o_card_popover_close`);
    expect.verifySteps(["close"]);
});

test("with rootClass props", async () => {
    await mountCardPopover({ rootClass: "my_custom_root_class" });
    expect(`.my_custom_root_class`).toHaveCount(1);
});

test(`templates with t-if using a field declared out of the templates`, async () => {
    await mountCardPopover({
        popoverNode: parseXML(`
            <popover>
                <field name="email"/>
                <templates>
                    <t t-name="popover-header">
                        <span class="o_custom_header" t-if="record.email.raw_value">
                            header
                        </span>
                        <span class="not_displayed" t-if="!record.email.raw_value">
                            not displayed
                        </span>
                    </t>
                    <t t-name="popover-body">
                        <span class="o_custom_body">Body</span>
                        <span class="not_displayed" t-if="!record.email.raw_value">
                            not displayed
                        </span>
                    </t>
                    <t t-name="popover-footer">
                        <button class="btn btn-secondary o_custom_footer_button" t-if="record.email.raw_value">
                            footer button
                        </button>
                        <span class="not_displayed" t-if="!record.email.raw_value">
                            not displayed
                        </span>
                    </t>
                </templates>
            </popover>
        `),
    });
    expect(`.o_popover_header .o_custom_header`).toHaveCount(1);
    expect(`.o_popover_body .o_custom_body`).toHaveCount(1);
    expect(`.o_popover_footer .o_custom_footer_button`).toHaveCount(1);
    expect(`.not_displayed`).toHaveCount(0);
});

test("template in arch get favors vs card_id attribute", async () => {
    await mountCardPopover({
        popoverNode: parseXML(`
            <popover card_id="1">
                <templates>
                    <t t-name="popover-body">
                        <div class="o_inline_body">
                            <field name="display_name"/>
                        </div>
                    </t>
                </templates>
            </popover>
        `),
    });
    expect(`.o_popover_body .o_inline_body`).toHaveCount(1);
    expect(`.o_popover_body .o_custom_card_body`).toHaveCount(0);
    expect(`.o_popover_body`).toHaveText("Jean Michel");
});
