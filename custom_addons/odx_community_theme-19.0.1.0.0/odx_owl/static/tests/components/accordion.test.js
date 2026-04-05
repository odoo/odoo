/** @odoo-module **/

import { expect, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import {
    Accordion,
    AccordionContent,
    AccordionHeader,
    AccordionItem,
    AccordionTrigger,
} from "@odx_owl/components/accordion/accordion";

test("horizontal accordion reverses left and right keyboard movement in rtl and skips disabled items", async () => {
    class Parent extends Component {
        static components = {
            Accordion,
            AccordionContent,
            AccordionHeader,
            AccordionItem,
            AccordionTrigger,
        };
        static template = xml`
            <Accordion dir="'rtl'" orientation="'horizontal'">
                <AccordionItem value="'one'">
                    <AccordionHeader>
                        <AccordionTrigger>One</AccordionTrigger>
                    </AccordionHeader>
                    <AccordionContent>Panel one</AccordionContent>
                </AccordionItem>
                <AccordionItem value="'two'" disabled="true">
                    <AccordionHeader>
                        <AccordionTrigger>Two</AccordionTrigger>
                    </AccordionHeader>
                    <AccordionContent>Panel two</AccordionContent>
                </AccordionItem>
                <AccordionItem value="'three'">
                    <AccordionHeader>
                        <AccordionTrigger>Three</AccordionTrigger>
                    </AccordionHeader>
                    <AccordionContent>Panel three</AccordionContent>
                </AccordionItem>
            </Accordion>
        `;
    }

    await mountWithCleanup(Parent);

    await contains(`.odx-accordion__item:first-child .odx-accordion__trigger`).focus();
    await contains(`.odx-accordion__item:first-child .odx-accordion__trigger`).press("ArrowLeft");

    expect(document.activeElement?.textContent?.trim()).toBe("Three");
    expect(document.querySelectorAll(".odx-accordion__trigger")[1]?.disabled).toBe(true);
});
