//-----------------------------------------------------------------------------
// ! PRODUCTION CODE: DO NOT TOUCH
//-----------------------------------------------------------------------------

import { Component, useEffect, useRef, xml } from "@odoo/owl";

export class ConvolutedElement extends Component {
    static props = {};
    static template = xml`
        <main t-ref="root">
            <input t-ref="input" value="42" />
            <ul>
                <li>Item<t t-out="nbsp" />1</li>
                <li>Item 2</li>
                <li>Item 3</li>
            </ul>
        </main>
    `;

    nbsp = "\u00a0";

    setup() {
        const inputRef = useRef("input");
        useEffect(
            (el) => el?.focus(),
            () => [inputRef.el]
        );
    }
}

export class ConvolutedElementWithIframe extends ConvolutedElement {
    static props = {};
    static template = xml`
        <main t-ref="root">
            <input t-ref="input" />
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
                <li>Item 3</li>
            </ul>
            <iframe srcdoc="&lt;p&gt;Hello&lt;/p&gt;" />
        </main>
    `;
}
