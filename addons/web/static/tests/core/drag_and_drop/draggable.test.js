import { drag, expect, queryAll, test } from "@odoo/hoot";
import { Component, htmlEscape, reactive, useEffect, useState, xml } from "@odoo/owl";
import { defineStyle, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { useDraggable } from "@web/core/drag_and_drop/draggable_hook";

/**
 * @param {string} template
 * @param {Component["setup"]} setup
 */
function mountConfigurableDraggable(template) {
    class SimpleComponent extends Component {
        static props = { params: Object };
        static template = template;

        setup() {
            useDraggable(this.props.params);
        }
    }

    const state = reactive({
        container: "",
        cursor: "",
        debug: true,
        delay: 0,
        elements: "",
        followCursor: true,
        groups: "",
        handle: "",
        optimistic: false,
        placeHolder: false,
        tolerance: 10,
        touchDelay: 300,
    });
    const selectionValues = {
        container: [
            ["", "None"],
            [".o-list", "List"],
            [".o-container", "Container"],
        ],
        cursor: [
            ["", "None"],
            ["pointer", "Pointer"],
            ["grabbing", "Grabbing"],
            ["move", "Move"],
        ],
        handle: [
            ["", "None"],
            [".o-handle", "Handle icon"],
        ],
    };

    return mountWithCleanup(
        class ConfigurableDraggable extends Component {
            static components = { SimpleComponent };
            static props = {};
            static template = xml`
                <div class="d-flex flex-row w-100 h-100">
                    <div class="d-flex flex-column w-25 m-2 gap-2">
                        <t t-foreach="state" t-as="property" t-key="property">
                            <label
                                class="d-flex cursor-pointer gap-1"
                                t-att-class="{ 'flex-column': typeof state[property] !== 'boolean' }"
                            >
                                <strong class="w-100">
                                    <t t-esc="propertyToLabel(property)" />
                                </strong>
                                <div>
                                    <t t-if="property in selectionValues">
                                        <select class="o_input" t-att-name="property" t-model="state[property]">
                                            <t t-foreach="selectionValues[property]" t-as="entry" t-key="entry[0]">
                                                <option t-att-value="entry[0]" t-esc="entry[1]" />
                                            </t>
                                        </select>
                                    </t>
                                    <t t-elif="typeof state[property] === 'boolean'">
                                        <input
                                            type="checkbox"
                                            class="form-check-input"
                                            t-att-name="property"
                                            t-model="state[property]"
                                        />
                                    </t>
                                    <t t-else="">
                                        <input
                                            type="text"
                                            class="o_input"
                                            t-att-placeholder="property"
                                            t-att-name="property"
                                            t-model="state[property]"
                                        />
                                    </t>
                                </div>
                            </label>
                        </t>
                    </div>
                    <div class="w-75 m-5">
                        <SimpleComponent params="state" t-key="Date.now()" />
                    </div>
                </div>
            `;

            setup() {
                this.selectionValues = selectionValues;
                this.state = useState(state);

                useEffect(this.onEffect, () => queryAll("iframe"));
            }

            onEffect(...iframes) {
                const styles = queryAll("style,link", { root: document.head });
                for (const iframe of iframes) {
                    iframe.addEventListener(
                        "load",
                        () => {
                            for (const style of styles) {
                                iframe.contentDocument.head?.appendChild(style.cloneNode(true));
                            }
                        },
                        { once: true }
                    );
                }
            }

            /**
             * @param {string} property
             */
            propertyToLabel(property) {
                const separated = property.replace(/([a-z])([A-Z])/g, "$1 $2");
                return separated[0].toUpperCase() + separated.slice(1);
            }
        }
    );
}

/**
 * @param {string} template
 * @param {Component["setup"]} setup
 */
function mountSimpleComponent(template, setup) {
    return mountWithCleanup(
        class SimpleComponent extends Component {
            static props = {};
            static template = template;

            setup() {
                setup.call(this);
            }
        }
    );
}

test("Draggable: simple list", async () => {
    await mountSimpleComponent(
        xml`
            <ul>
                <li class="p-2">First element</li>
                <li class="p-2">Second element</li>
                <li class="p-2">Last element</li>
            </ul>
        `,
        function setup() {
            useDraggable({
                elements: "li",
                placeHolder: true,
                tolerance: 0,
            });
        }
    );

    expect(".o-draggable-dragged").not.toHaveCount();

    const { drop } = await drag("li:first");

    expect(".o-draggable-dragged").toHaveCount(1);

    await drop("li:last");

    expect(".o-draggable-dragged").not.toHaveCount();
});

test("draggable playground ", async () => {
    defineStyle(/* css */ `
        .o-item {
            border: 5px var(--border-color) solid;
            padding: 1rem;

            &:hover {
                --border-color: var(--primary);
            }
        }

        .o-draggable-dragged {
            background-color: rgba(var(--primary-rgb), 0.2);
        }
    `);

    const iframeContent = /* xml */ `
        <ul class="o-list m-2 list-unstyled border border-5 border-success" style="height: 200vh;">
            <li class="o-item d-flex gap-2 align-items-center" draggable="">
                <span class="o-handle oi oi-draggable" />
                First iframe element
            </li>
            <li class="o-item d-flex gap-2 align-items-center" draggable="">
                <span class="o-handle oi oi-draggable" />
                Second iframe element
            </li>
            <li class="o-item d-flex gap-2 align-items-center" draggable="">
                <span class="o-handle oi oi-draggable" />
                Last iframe element
            </li>
        </ul>
    `;
    await mountConfigurableDraggable(
        xml`
            <div class="d-flex w-100 h-100 gap-2">
                <div class="o-container p-2 border border-5 border-danger overflow-auto">
                    <ul class="o-list m-2 list-unstyled border border-5 border-warning" style="width: 300vw; height: 300vh">
                        <li class="o-item d-flex gap-2 align-items-center" draggable="" style="width: 300px">
                            <span class="o-handle oi oi-draggable" />
                            First element
                        </li>
                        <li class="o-item d-flex gap-2 align-items-center" draggable="" style="width: 250px">
                            <span class="o-handle oi oi-draggable" />
                            Second element
                        </li>
                        <li class="o-item d-flex gap-2 align-items-center" draggable="" style="width: 350px">
                            <span class="o-handle oi oi-draggable" />
                            Last element
                        </li>
                    </ul>
                </div>
                <iframe class="border border-5 border-info" srcdoc="${htmlEscape(iframeContent)}" />
            </div>
        `
    );

    expect(".o_draggable").toHaveCount(3);
});
