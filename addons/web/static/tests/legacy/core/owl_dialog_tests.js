odoo.define('web.owl_dialog_tests', function (require) {
    "use strict";

    const LegacyDialog = require('web.Dialog');
    const FormView = require('web.FormView');
    const CalendarView = require('web.CalendarView');
    const makeTestEnvironment = require('web.test_env');
    const Dialog = require('web.OwlDialog');
    const testUtils = require('web.test_utils');
    const { registry } = require("@web/core/registry");
    const legacyViewRegistry = require('web.view_registry');

    const { makeLegacyDialogMappingTestEnv } = require('@web/../tests/helpers/legacy_env_utils');
    const { Dialog: WowlDialog } = require("@web/core/dialog/dialog");
    const { WithEnv } = require("@web/core/utils/components");
    const {
        getFixture,
        nextTick,
        mount,
        destroy,
    } = require("@web/../tests/helpers/utils");
    const { createWebClient, doAction } = require("@web/../tests/webclient/helpers");
    const { LegacyComponent } = require("@web/legacy/legacy_component");

    const { Component, useState, xml } = owl;
    const EscapeKey = { key: 'Escape', keyCode: 27, which: 27 };

    QUnit.module('core', {}, function () {
        QUnit.module('OwlDialog');

        QUnit.test("Rendering of all props", async function (assert) {
            assert.expect(36);

            class SubComponent extends LegacyComponent {
                // Handlers
                _onClick() {
                    assert.step('subcomponent_clicked');
                }
            }
            SubComponent.template = xml`<div class="o_subcomponent" t-esc="props.text" t-on-click="_onClick"/>`;

            class Parent extends LegacyComponent {
                setup() {
                    this.state = useState({ textContent: "sup" });
                }
                // Handlers
                _onButtonClicked() {
                    assert.step('button_clicked');
                }
                _onDialogClosed() {
                    assert.step('dialog_closed');
                }
            }
            Parent.components = { Dialog, SubComponent };
            Parent.template = xml`
                <Dialog
                    backdrop="state.backdrop"
                    contentClass="state.contentClass"
                    fullscreen="state.fullscreen"
                    renderFooter="state.renderFooter"
                    renderHeader="state.renderHeader"
                    size="state.size"
                    subtitle="state.subtitle"
                    technical="state.technical"
                    title="state.title"
                    onClosed="_onDialogClosed"
                    >
                    <SubComponent text="state.textContent"/>
                    <t t-set-slot="buttons">
                        <button class="btn btn-primary" t-on-click="_onButtonClicked">The Button</button>
                    </t>
                </Dialog>`;

            const parent = await mount(Parent, getFixture(), {
                env: makeTestEnvironment(),
            });
            const dialog = document.querySelector('.o_dialog');

            // Helper function
            async function changeProps(key, value) {
                parent.state[key] = value;
                await testUtils.nextTick();
            }

            // Basic layout with default properties
            assert.containsOnce(dialog, '.modal.o_technical_modal');
            assert.hasClass(dialog.querySelector('.modal .modal-dialog'), 'modal-lg');
            assert.containsOnce(dialog, '.modal-header > button.btn-close');
            assert.containsOnce(dialog, '.modal-footer > button.btn.btn-primary');
            assert.strictEqual(dialog.querySelector('.modal-body').innerText.trim(), "sup",
                "Subcomponent should match with its given text");

            // Backdrop (default: 'static')
            // Static backdrop click should focus first button
            // => we need to reset that property
            dialog.querySelector('.btn-primary').blur(); // Remove the focus explicitely
            assert.containsNone(document.body, '.modal-backdrop'); // No backdrop *element* for Odoo modal...
            assert.notEqual(window.getComputedStyle(dialog.querySelector('.modal')).backgroundColor, 'rgba(0, 0, 0, 0)'); // ... but a non transparent modal
            await testUtils.dom.click(dialog.querySelector('.modal'));
            assert.strictEqual(document.activeElement, dialog.querySelector('.btn-primary'),
                "Button should be focused when clicking on backdrop");
            assert.verifySteps([]); // Ensure not closed
            dialog.querySelector('.btn-primary').blur(); // Remove the focus explicitely

            await changeProps('backdrop', false);
            assert.containsNone(document.body, '.modal-backdrop'); // No backdrop *element* for Odoo modal...
            assert.strictEqual(window.getComputedStyle(dialog.querySelector('.modal')).backgroundColor, 'rgba(0, 0, 0, 0)');
            await testUtils.dom.click(dialog.querySelector('.modal'));
            assert.notEqual(document.activeElement, dialog.querySelector('.btn-primary'),
                "Button should not be focused when clicking on backdrop 'false'");
            assert.verifySteps([]); // Ensure not closed

            await changeProps('backdrop', true);
            assert.containsNone(document.body, '.modal-backdrop'); // No backdrop *element* for Odoo modal...
            assert.notEqual(window.getComputedStyle(dialog.querySelector('.modal')).backgroundColor, 'rgba(0, 0, 0, 0)'); // ... but a non transparent modal
            await testUtils.dom.click(dialog.querySelector('.modal'));
            assert.notEqual(document.activeElement, dialog.querySelector('.btn-primary'),
                "Button should not be focused when clicking on backdrop 'true'");
            assert.verifySteps(['dialog_closed']);

            // Dialog class (default: '')
            await changeProps('contentClass', 'my_dialog_class');
            assert.hasClass(dialog.querySelector('.modal-content'), 'my_dialog_class');

            // Full screen (default: false)
            assert.doesNotHaveClass(dialog.querySelector('.modal'), 'o_modal_full');
            await changeProps('fullscreen', true);
            assert.hasClass(dialog.querySelector('.modal'), 'o_modal_full');

            // Size class (default: 'large')
            await changeProps('size', 'extra-large');
            assert.strictEqual(dialog.querySelector('.modal-dialog').className, 'modal-dialog modal-xl',
                "Modal should have taken the class modal-xl");
            await changeProps('size', 'medium');
            assert.strictEqual(dialog.querySelector('.modal-dialog').className, 'modal-dialog',
                "Modal should not have any additionnal class with 'medium'");
            await changeProps('size', 'small');
            assert.strictEqual(dialog.querySelector('.modal-dialog').className, 'modal-dialog modal-sm',
                "Modal should have taken the class modal-sm");

            // Subtitle (default: '')
            await changeProps('subtitle', "The Subtitle");
            assert.strictEqual(dialog.querySelector('span.o_subtitle').innerText.trim(), "The Subtitle",
                "Subtitle should match with its given text");

            // Technical (default: true)
            assert.hasClass(dialog.querySelector('.modal'), 'o_technical_modal');
            await changeProps('technical', false);
            assert.doesNotHaveClass(dialog.querySelector('.modal'), 'o_technical_modal');

            // Title (default: 'Odoo')
            assert.strictEqual(dialog.querySelector('h4.modal-title').innerText.trim(), "Odoo" + "The Subtitle",
                "Title should match with its default text");
            await changeProps('title', "The Title");
            assert.strictEqual(dialog.querySelector('h4.modal-title').innerText.trim(), "The Title" + "The Subtitle",
                "Title should match with its given text");

            // Reactivity of buttons
            await testUtils.dom.click(dialog.querySelector('.modal-footer .btn-primary'));
            assert.verifySteps(["button_clicked"]);

            // Render footer (default: true)
            await changeProps('renderFooter', false);
            assert.containsNone(dialog, '.modal-footer');

            // Render header (default: true)
            await changeProps('renderHeader', false);
            assert.containsNone(dialog, '.header');

            // Reactivity of subcomponents
            await changeProps('textContent', "wassup");
            assert.strictEqual(dialog.querySelector('.o_subcomponent').innerText.trim(), "wassup",
                "Subcomponent should match with its given text");
            await testUtils.dom.click(dialog.querySelector('.o_subcomponent'));

            assert.verifySteps(["subcomponent_clicked"]);
        });

        QUnit.test("Interactions between multiple dialogs", async function (assert) {
            assert.expect(23);

            const { legacyEnv } = await makeLegacyDialogMappingTestEnv();
            class Parent extends LegacyComponent {
                setup() {
                    this.dialogIds = useState([]);
                }
                // Handlers
                _onDialogClosed(id) {
                    assert.step(`dialog_${id}_closed`);
                    this.dialogIds.splice(this.dialogIds.findIndex(d => d === id), 1);
                }
            }
            Parent.components = { Dialog };
            Parent.template = xml`
                <div>
                    <Dialog t-foreach="dialogIds" t-as="dialogId" t-key="dialogId"
                        contentClass="'dialog_' + dialogId" onClosed="() => this._onDialogClosed(dialogId)"
                        />
                </div>`;

            const parent = await mount(Parent, getFixture(), {
                env: legacyEnv,
            });

            // Dialog 1 : Owl
            parent.dialogIds.push(1);
            await testUtils.nextTick();
            // Dialog 2 : Legacy
            new LegacyDialog(null, {}).open();
            await testUtils.nextTick();
            // Dialog 3 : Legacy
            new LegacyDialog(null, {}).open();
            await testUtils.nextTick();
            // Dialog 4 : Owl
            parent.dialogIds.push(4);
            await testUtils.nextTick();
            // Dialog 5 : Owl
            parent.dialogIds.push(5);
            await testUtils.nextTick();
            // Dialog 6 : Legacy (unopened)
            const unopenedModal = new LegacyDialog(null, {});
            await testUtils.nextTick();

            // Manually closes the last legacy dialog. Should not affect the other
            // existing dialogs (3 owl and 2 legacy).
            unopenedModal.close();
            assert.containsN(document.body, ".modal", 5);

            let modals = document.querySelectorAll('.modal');
            assert.notOk(modals[modals.length - 1].classList.contains('o_inactive_modal'),
                "last dialog should have the active class");
            assert.notOk(modals[modals.length - 1].classList.contains('o_legacy_dialog'),
                "active dialog should not have the legacy class");
            assert.containsN(document.body, '.o_dialog', 3);
            assert.containsN(document.body, '.o_legacy_dialog', 2);

            // Reactivity with owl dialogs
            await testUtils.dom.triggerEvent(modals[modals.length - 1], 'keydown', EscapeKey); // Press Escape

            modals = document.querySelectorAll('.modal');
            assert.notOk(modals[modals.length - 1].classList.contains('o_inactive_modal'),
                "last dialog should have the active class");
            assert.notOk(modals[modals.length - 1].classList.contains('o_legacy_dialog'),
                "active dialog should not have the legacy class");
            assert.containsN(document.body, '.o_dialog', 2);
            assert.containsN(document.body, '.o_legacy_dialog', 2);

            await testUtils.dom.click(modals[modals.length - 1].querySelector('.btn.btn-primary')); // Click on 'Ok' button

            modals = document.querySelectorAll('.modal');
            assert.containsOnce(document.body, '.modal.o_legacy_dialog:not(.o_inactive_modal)',
                "active dialog should have the legacy class");
            assert.containsOnce(document.body, '.o_dialog');
            assert.containsN(document.body, '.o_legacy_dialog', 2);

            // Reactivity with legacy dialogs
            await testUtils.dom.triggerEvent(modals[modals.length - 1], 'keydown', EscapeKey);

            modals = document.querySelectorAll('.modal');
            assert.containsOnce(document.body, '.modal.o_legacy_dialog:not(.o_inactive_modal)',
                "active dialog should have the legacy class");
            assert.containsOnce(document.body, '.o_dialog');
            assert.containsOnce(document.body, '.o_legacy_dialog');

            await testUtils.dom.click(modals[modals.length - 1].querySelector('.btn-close'));

            modals = document.querySelectorAll('.modal');
            assert.notOk(modals[modals.length - 1].classList.contains('o_inactive_modal'),
                "last dialog should have the active class");
            assert.notOk(modals[modals.length - 1].classList.contains('o_legacy_dialog'),
                "active dialog should not have the legacy class");
            assert.containsOnce(document.body, '.o_dialog');
            assert.containsNone(document.body, '.o_legacy_dialog');

            destroy(parent);

            assert.containsNone(document.body, '.modal');
            // dialog 1 is closed through the removal of its parent => no callback
            assert.verifySteps(['dialog_5_closed', 'dialog_4_closed']);
        });

        QUnit.test("Interactions between legacy owl dialogs and new owl dialogs", async function (assert) {
            assert.expect(9);
            const { legacyEnv, env } = await makeLegacyDialogMappingTestEnv();

            class OwlDialogWrapper extends LegacyComponent {
                setup() {
                    this.env = legacyEnv;
                    this.__owl__.childEnv = legacyEnv;
                }
            }
            OwlDialogWrapper.template = xml`
                <Dialog
                onClosed="() => props.close()"
                />
            `;
            OwlDialogWrapper.components = { Dialog };
            class WowlDialogWrapper extends Component {}
            WowlDialogWrapper.components = { WowlDialog };
            WowlDialogWrapper.template = xml`<WowlDialog contentClass="props.contentClass">content</WowlDialog>`;
            class Parent extends LegacyComponent {
                setup() {
                    this.dialogs = useState([]);
                }
                // Handlers
                _onDialogClosed(id) {
                    assert.step(`dialog_${id}_closed`);
                    this.dialogs.splice(this.dialogs.findIndex(d => d.id === id), 1);
                }
            }
            Parent.template = xml`
                <div>
                    <div class="o_dialog_container"/>
                    <t t-foreach="dialogs" t-as="dialog" t-key="dialog.id">
                        <WithEnv env="{ dialogData: { isActive: true, close: () => this._onDialogClosed(dialog.id) } }">
                            <t t-component="dialog.class"
                                contentClass="'dialog_' + dialog.id"
                                close="() => this._onDialogClosed(dialog.id)"
                            />
                        </WithEnv>
                    </t>
                </div>`;
            Parent.components = { WithEnv };

            const target = getFixture();
            const parent = await mount(Parent, target, { env });

            parent.dialogs.push({ id: 1, class: WowlDialogWrapper });
            await nextTick();
            parent.dialogs.push({ id: 2, class: OwlDialogWrapper });
            await nextTick();
            parent.dialogs.push({ id: 3, class: WowlDialogWrapper });
            await nextTick();

            assert.verifySteps([]);
            assert.containsN(document.body, ".modal", 3);
            await testUtils.dom.triggerEvent(document.activeElement, 'keydown', EscapeKey); // Press Escape
            assert.verifySteps(['dialog_3_closed']);
            await testUtils.dom.triggerEvent(document.activeElement, 'keydown', EscapeKey); // Press Escape
            assert.verifySteps(['dialog_2_closed']);
            await testUtils.dom.triggerEvent(document.activeElement, 'keydown', EscapeKey); // Press Escape
            assert.verifySteps(['dialog_1_closed']);
            await nextTick();
            assert.containsNone(document.body, ".modal");
        });

        QUnit.test("Z-index toggling and interactions", async function (assert) {
            assert.expect(3);

            function createCustomModal(className) {
                const $modal = $(
                    `<div role="dialog" class="${className}" tabindex="-1">
                        <div class="modal-dialog medium">
                            <div class="modal-content">
                                <main class="modal-body">The modal body</main>
                            </div>
                        </div>
                    </div>`
                ).appendTo('body').modal('show');
                const modal = $modal[0];
                modal.destroy = function () {
                    $modal.modal('hide');
                    this.remove();
                };
                return modal;
            }

            class Parent1 extends LegacyComponent {
                setup() {
                }
            }
            Parent1.components = { Dialog };
            Parent1.template = xml`
                <div>
                    <Dialog/>
                </div>`;

            const parent1 = await mount(Parent1, getFixture(), {
                env: makeTestEnvironment(),
            });

            class Parent2 extends LegacyComponent {
                setup() {
                    this.state = useState({ showSecondDialog: true });
                }
            }
            Parent2.components = { Dialog };
            Parent2.template = xml`
                <div>
                    <Dialog t-if="state.showSecondDialog"/>
                </div>`;

            const parent2 = await mount(Parent2, getFixture(), {
                env: makeTestEnvironment(),
            });

            const frontEndModal = createCustomModal('modal');
            const backEndModal = createCustomModal('modal o_technical_modal');

            // querySelector will target the first modal (the static one).
            const owlIndexBefore = getComputedStyle(document.querySelector('.o_dialog .modal')).zIndex;
            const feZIndexBefore = getComputedStyle(frontEndModal).zIndex;
            const beZIndexBefore = getComputedStyle(backEndModal).zIndex;

            parent2.state.showSecondDialog = false;
            await testUtils.nextTick();

            assert.ok(owlIndexBefore < getComputedStyle(document.querySelector('.o_dialog .modal')).zIndex,
                "z-index of the owl dialog should be incremented since the active modal was destroyed");
            assert.strictEqual(feZIndexBefore, getComputedStyle(frontEndModal).zIndex,
                "z-index of front-end modals should not be impacted by Owl Dialog activity system");
            assert.strictEqual(beZIndexBefore, getComputedStyle(backEndModal).zIndex,
                "z-index of custom back-end modals should not be impacted by Owl Dialog activity system");

            frontEndModal.destroy();
            backEndModal.destroy();
            destroy(parent1);
            destroy(parent2);
        });

        QUnit.test("remove tabindex on inactive dialog", async (assert) => {
            registry.category("views").remove("calendar"); // remove new calendar from registry
            registry.category("views").remove("form"); // remove new form from registry
            legacyViewRegistry.add("form", FormView); // add legacy form -> will be wrapped and added to new registry
            legacyViewRegistry.add("calendar", CalendarView); // add legacy calendar -> will be wrapped and added to new registry

            const serverData = {
                actions: {
                    1: {
                        id: 1,
                        flags: { initialDate: new Date(2020, 6, 13) },
                        name: "Test",
                        res_model: "event",
                        type: "ir.actions.act_window",
                        views: [[false, "calendar"]],
                    },
                    2: {
                        id: 2,
                        name: "Test",
                        res_model: "event",
                        target: "new",
                        type: "ir.actions.act_window",
                        views: [[2, "form"]],
                    },
                },
                models: {
                    event: {
                        fields: {
                            id: { type: "integer" },
                            display_name: { type: "char" },
                            start: { type: "date" },
                        },
                        records: [{ id: 1, display_name: "Event 1", start: "2020-07-13" }],
                        methods: {
                            async check_access_rights() {
                                return true;
                            },
                            async get_formview_id() {
                                return false;
                            },
                        },
                    },
                },
                views: {
                    "event,false,calendar": `<calendar date_start="start" event_open_popup="true" />`,
                    "event,false,search": `<search />`,
                    "event,false,form": `
                        <form><sheet>
                            <field name="display_name" />
                            <button type="action" name="2">Click me</button>
                        </sheet></form>
                    `,
                    "event,2,form": `<form><sheet><field name="display_name" /></sheet></form>`,
                },
                activateMockServer: true,
            };

            const target = getFixture();
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 1);

            await testUtils.dom.click(target.querySelector(`.fc-event[data-event-id="1"]`));
            await testUtils.dom.click(target.querySelector(`.o_cw_popover_edit`));

            assert.containsNone(target, ".o_dialog");
            assert.containsOnce(target, ".modal");
            assert.containsOnce(target, ".modal[tabindex='-1']");

            assert.strictEqual(
                target.querySelector(`.o_field_widget[name="display_name"]`).value,
                "Event 1"
            );
            await testUtils.fields.editInput(
                target.querySelector(`.o_field_widget[name="display_name"]`),
                "legacy"
            );
            assert.strictEqual(
                target.querySelector(`.o_field_widget[name="display_name"]`).value,
                "legacy"
            );

            await testUtils.dom.click(target.querySelector(`button[name="2"]`));
            assert.containsOnce(target, ".o_dialog");
            assert.containsN(target, ".modal", 2);
            assert.containsOnce(target, ".modal:not([tabindex='-1'])");
            assert.containsOnce(target, ".o_dialog .modal[tabindex='-1']");

            assert.strictEqual(
                target.querySelector(`.o_dialog .o_field_widget[name="display_name"]`).value,
                ""
            );
            await testUtils.fields.editInput(
                target.querySelector(`.o_dialog .o_field_widget[name="display_name"]`),
                "wowl"
            );
            assert.strictEqual(
                target.querySelector(`.o_dialog .o_field_widget[name="display_name"]`).value,
                "wowl"
            );

            await testUtils.dom.click(target.querySelector(`.o_dialog .modal-header .btn-close`));
            assert.containsNone(target, ".o_dialog");
            assert.containsOnce(target, ".modal");
            assert.containsOnce(target, ".modal[tabindex='-1']");

            await testUtils.dom.click(target.querySelector(`.modal-header .btn-close`));
            assert.containsNone(target, ".o_dialog");
            assert.containsNone(target, ".modal");
        });
    });
});
