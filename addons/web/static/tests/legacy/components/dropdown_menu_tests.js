odoo.define('web.dropdown_menu_tests', function (require) {
    "use strict";

    const DropdownMenu = require('web.DropdownMenu');
    const testUtils = require('web.test_utils');

    const { createComponent } = testUtils;

    QUnit.module('Components', {
        beforeEach: function () {
            this.items = [
                {
                    isActive: false,
                    description: 'Some Item',
                    id: 1,
                    groupId: 1,
                    groupNumber: 1,
                    options: [
                        { description: "First Option", groupNumber: 1, id: 1 },
                        { description: "Second Option", groupNumber: 2, id: 2 },
                    ],
                }, {
                    isActive: true,
                    description: 'Some other Item',
                    id: 2,
                    groupId: 2,
                    groupNumber: 2,
                },
            ];
        },
    }, function () {
        QUnit.module('DropdownMenu');

        QUnit.test('simple rendering and basic interactions', async function (assert) {
            assert.expect(8);

            const dropdown = await createComponent(DropdownMenu, {
                props: {
                    items: this.items,
                    title: "Dropdown",
                },
            });

            assert.strictEqual(dropdown.el.querySelector('button').innerText.trim(), "Dropdown");
            assert.containsNone(dropdown, '.dropdown-menu');

            await testUtils.dom.click(dropdown.el.querySelector('button'));

            assert.containsN(dropdown, '.dropdown-divider, .dropdown-item', 3,
                'should have 3 elements counting the divider');
            const itemEls = dropdown.el.querySelectorAll('.o_menu_item > .dropdown-item');
            assert.strictEqual(itemEls[0].innerText.trim(), 'Some Item');
            assert.doesNotHaveClass(itemEls[0], 'selected');
            assert.hasClass(itemEls[1], 'selected');

            const dropdownElements = dropdown.el.querySelectorAll('.o_menu_item *');
            for (const dropdownEl of dropdownElements) {
                await testUtils.dom.click(dropdownEl);
            }
            assert.containsOnce(dropdown, '.dropdown-menu',
                "Clicking on any item of the dropdown should not close it");

            await testUtils.dom.click(document.body);

            assert.containsNone(dropdown, '.dropdown-menu',
                "Clicking outside of the dropdown should close it");

            dropdown.destroy();
        });

        QUnit.test('only one dropdown rendering at same time (owl vs bootstrap dropdown)', async function (assert) {
            assert.expect(12);

            const bsDropdown = document.createElement('div');
            bsDropdown.innerHTML = `<div class="dropdown">
                <button class="btn dropdown-toggle" type="button" 
                        data-toggle="dropdown" aria-expanded="false">
                    BS Dropdown button
                </button>
                <div class="dropdown-menu">
                    <a class="dropdown-item" href="#">BS Action</a>
                </div>
            </div>`;
            document.body.append(bsDropdown);

            const dropdown = await createComponent(DropdownMenu, {
                props: {
                    items: this.items,
                    title: "Dropdown",
                },
            });

            await testUtils.dom.click(dropdown.el.querySelector('button'));

            assert.hasClass(dropdown.el.querySelector('.dropdown-menu'), 'show');
            assert.doesNotHaveClass(bsDropdown.querySelector('.dropdown-menu'), 'show');

            assert.isVisible(dropdown.el.querySelector('.dropdown-menu'),
                "owl dropdown menu should be visible");
            assert.isNotVisible(bsDropdown.querySelector('.dropdown-menu'),
                "bs dropdown menu should not be visible");

            await testUtils.dom.click(bsDropdown.querySelector('.btn.dropdown-toggle'));

            assert.doesNotHaveClass(dropdown.el, 'show');
            assert.containsNone(dropdown.el, '.dropdown-menu',
                "owl dropdown menu should not be set inside the dom");

            assert.hasClass(bsDropdown.querySelector('.dropdown-menu'), 'show');
            assert.isVisible(bsDropdown.querySelector('.dropdown-menu'),
                "bs dropdown menu should be visible");

            await testUtils.dom.click(document.body);

            assert.doesNotHaveClass(dropdown.el, 'show');
            assert.containsNone(dropdown.el, '.dropdown-menu',
                "owl dropdown menu should not be set inside the dom");

            assert.doesNotHaveClass(bsDropdown.querySelector('.dropdown-menu'), 'show');
            assert.isNotVisible(bsDropdown.querySelector('.dropdown-menu'),
                "bs dropdown menu should not be visible");

            bsDropdown.remove();
            dropdown.destroy();
        });

        QUnit.test('click on an item without options should toggle it', async function (assert) {
            assert.expect(7);

            delete this.items[0].options;

            const dropdown = await createComponent(DropdownMenu, {
                props: { items: this.items },
                intercepts: {
                    'item-selected': function (ev) {
                        assert.strictEqual(ev.detail.item.id, 1);
                        this.state.items[0].isActive = !this.state.items[0].isActive;
                    },
                }
            });

            await testUtils.dom.click(dropdown.el.querySelector('button'));

            const firstItemEl = dropdown.el.querySelector('.o_menu_item > a');
            assert.doesNotHaveClass(firstItemEl, 'selected');
            await testUtils.dom.click(firstItemEl);
            assert.hasClass(firstItemEl, 'selected');
            assert.isVisible(firstItemEl);
            await testUtils.dom.click(firstItemEl);
            assert.doesNotHaveClass(firstItemEl, 'selected');
            assert.isVisible(firstItemEl);

            dropdown.destroy();
        });

        QUnit.test('click on an item should not change url', async function (assert) {
            assert.expect(1);

            delete this.items[0].options;

            const initialHref = window.location.href;
            const dropdown = await createComponent(DropdownMenu, {
                props: { items: this.items },
            });

            await testUtils.dom.click(dropdown.el.querySelector('button'));
            await testUtils.dom.click(dropdown.el.querySelector('.o_menu_item > a'));
            assert.strictEqual(window.location.href, initialHref,
                "the url should not have changed after a click on an item");

            dropdown.destroy();
        });

        QUnit.test('options rendering', async function (assert) {
            assert.expect(6);

            const dropdown = await createComponent(DropdownMenu, {
                props: { items: this.items },
            });

            await testUtils.dom.click(dropdown.el.querySelector('button'));
            assert.containsN(dropdown, '.dropdown-divider, .dropdown-item', 3);

            const firstItemEl = dropdown.el.querySelector('.o_menu_item > a');
            assert.hasClass(firstItemEl.querySelector('i'), 'o_icon_right fa fa-caret-right');
            // open options menu
            await testUtils.dom.click(firstItemEl);
            assert.hasClass(firstItemEl.querySelector('i'), 'o_icon_right fa fa-caret-down');
            assert.containsN(dropdown, '.dropdown-divider, .dropdown-item', 6);

            // close options menu
            await testUtils.dom.click(firstItemEl);
            assert.hasClass(firstItemEl.querySelector('i'), 'o_icon_right fa fa-caret-right');
            assert.containsN(dropdown, '.dropdown-divider, .dropdown-item', 3);

            dropdown.destroy();
        });

        QUnit.test('close menu closes also submenus', async function (assert) {
            assert.expect(2);

            const dropdown = await createComponent(DropdownMenu, {
                props: { items: this.items },
            });

            // open dropdown menu
            await testUtils.dom.click(dropdown.el.querySelector('button'));
            // open options menu of first item
            await testUtils.dom.click(dropdown.el.querySelector('.o_menu_item a'));

            assert.containsN(dropdown, '.dropdown-divider, .dropdown-item', 6);
            await testUtils.dom.click(dropdown.el.querySelector('button'));

            await testUtils.dom.click(dropdown.el.querySelector('button'));
            assert.containsN(dropdown, '.dropdown-divider, .dropdown-item', 3);

            dropdown.destroy();
        });

        QUnit.test('click on an option should trigger the event "item_option_clicked" with appropriate data', async function (assert) {
            assert.expect(18);

            let eventNumber = 0;
            const dropdown = await createComponent(DropdownMenu, {
                props: { items: this.items },
                intercepts: {
                    'item-selected': function (ev) {
                        eventNumber++;
                        const { option } = ev.detail;
                        assert.strictEqual(ev.detail.item.id, 1);
                        if (eventNumber === 1) {
                            assert.strictEqual(option.id, 1);
                            this.state.items[0].isActive = true;
                            this.state.items[0].options[0].isActive = true;
                        }
                        if (eventNumber === 2) {
                            assert.strictEqual(option.id, 2);
                            this.state.items[0].options[1].isActive = true;
                        }
                        if (eventNumber === 3) {
                            assert.strictEqual(option.id, 1);
                            this.state.items[0].options[0].isActive = false;
                        }
                        if (eventNumber === 4) {
                            assert.strictEqual(option.id, 2);
                            this.state.items[0].isActive = false;
                            this.state.items[0].options[1].isActive = false;
                        }
                    },
                }
            });

            // open dropdown menu
            await testUtils.dom.click(dropdown.el.querySelector('button'));
            assert.containsN(dropdown, '.dropdown-divider, .o_menu_item', 3);

            // open menu options of first item
            await testUtils.dom.click(dropdown.el.querySelector('.o_menu_item > a'));
            let optionELs = dropdown.el.querySelectorAll('.o_menu_item .o_item_option > a');

            // click on first option
            await testUtils.dom.click(optionELs[0]);
            assert.hasClass(dropdown.el.querySelector('.o_menu_item > a'), 'selected');
            optionELs = dropdown.el.querySelectorAll('.o_menu_item .o_item_option > a');
            assert.hasClass(optionELs[0], 'selected');
            assert.doesNotHaveClass(optionELs[1], 'selected');

            // click on second option
            await testUtils.dom.click(optionELs[1]);
            assert.hasClass(dropdown.el.querySelector('.o_menu_item > a'), 'selected');
            optionELs = dropdown.el.querySelectorAll('.o_menu_item .o_item_option > a');
            assert.hasClass(optionELs[0], 'selected');
            assert.hasClass(optionELs[1], 'selected');

            // click again on first option
            await testUtils.dom.click(optionELs[0]);
            // click again on second option
            await testUtils.dom.click(optionELs[1]);
            assert.doesNotHaveClass(dropdown.el.querySelector('.o_menu_item > a'), 'selected');
            optionELs = dropdown.el.querySelectorAll('.o_menu_item .o_item_option > a');
            assert.doesNotHaveClass(optionELs[0], 'selected');
            assert.doesNotHaveClass(optionELs[1], 'selected');

            dropdown.destroy();
        });

        QUnit.test('keyboard navigation', async function (assert) {
            assert.expect(12);

            // Shorthand method to trigger a specific keydown.
            // Note that BootStrap handles some of the navigation moves (up and down)
            // so we need to give the event the proper "which" property. We also give
            // it when it's not required to check if it has been correctly prevented.
            async function navigate(key, global) {
                const which = {
                    Enter: 13,
                    Escape: 27,
                    ArrowLeft: 37,
                    ArrowUp: 38,
                    ArrowRight: 39,
                    ArrowDown: 40,
                }[key];
                const target = global ? document.body : document.activeElement;
                await testUtils.dom.triggerEvent(target, 'keydown', { key, which });
                if (key === 'Enter') {
                    // Pressing "Enter" on a focused element triggers a click (HTML5 specs)
                    await testUtils.dom.click(target);
                }
            }

            const dropdown = await createComponent(DropdownMenu, {
                props: { items: this.items },
            });

            // Initialize active element (start at toggle button)
            dropdown.el.querySelector('button').focus();
            await testUtils.dom.click(dropdown.el.querySelector('button'));

            await navigate('ArrowDown'); // Go to next item

            assert.strictEqual(document.activeElement, dropdown.el.querySelector('.o_menu_item a'));
            assert.containsNone(dropdown, '.o_item_option');

            await navigate('ArrowRight'); // Unfold first item's options (w/ Right)

            assert.strictEqual(document.activeElement, dropdown.el.querySelector('.o_menu_item a'));
            assert.containsN(dropdown, '.o_item_option', 2);

            await navigate('ArrowDown'); // Go to next option

            assert.strictEqual(document.activeElement, dropdown.el.querySelector('.o_item_option a'));

            await navigate('ArrowLeft'); // Fold first item's options (w/ Left)

            assert.strictEqual(document.activeElement, dropdown.el.querySelector('.o_menu_item a'));
            assert.containsNone(dropdown, '.o_item_option');

            await navigate('Enter'); // Unfold first item's options (w/ Enter)

            assert.strictEqual(document.activeElement, dropdown.el.querySelector('.o_menu_item a'));
            assert.containsN(dropdown, '.o_item_option', 2);

            await navigate('ArrowDown'); // Go to next option
            await navigate('Escape'); // Fold first item's options (w/ Escape)
            await testUtils.nextTick();

            assert.strictEqual(dropdown.el.querySelector('.o_menu_item a'), document.activeElement);
            assert.containsNone(dropdown, '.o_item_option');

            await navigate('Escape', true); // Close the dropdown

            assert.containsNone(dropdown, '.dropdown-menu', "Dropdown should be folded");

            dropdown.destroy();
        });

        QUnit.test('interactions between multiple dropdowns', async function (assert) {
            assert.expect(7);

            const props = { items: this.items };
            class Parent extends owl.Component {
                constructor() {
                    super(...arguments);
                    this.state = owl.useState(props);
                }
            }
            Parent.components = { DropdownMenu };
            Parent.template = owl.tags.xml`
                <div>
                    <DropdownMenu class="first" title="'First'" items="state.items"/>
                    <DropdownMenu class="second" title="'Second'" items="state.items"/>
                </div>`;
            const parent = new Parent();
            await parent.mount(testUtils.prepareTarget(), { position: 'first-child' });

            const [menu1, menu2] = parent.el.querySelectorAll('.dropdown');

            assert.containsNone(parent, '.dropdown-menu');

            await testUtils.dom.click(menu1.querySelector('button'));

            assert.containsOnce(parent, '.dropdown-menu');
            assert.containsOnce(parent, '.dropdown.first .dropdown-menu');

            await testUtils.dom.click(menu2.querySelector('button'));

            assert.containsOnce(parent, '.dropdown-menu');
            assert.containsOnce(parent, '.dropdown.second .dropdown-menu');

            await testUtils.dom.click(menu2.querySelector('.o_menu_item a'));
            await testUtils.dom.click(menu1.querySelector('button'));

            assert.containsOnce(parent, '.dropdown-menu');
            assert.containsOnce(parent, '.dropdown.first .dropdown-menu');

            parent.destroy();
        });

        QUnit.test("dropdown doesn't get close on mousedown inside and mouseup outside dropdown", async function (assert) {
            // In this test, we simulate a case where the user clicks inside a dropdown menu item
            // (e.g. in the input of the 'Save current search' item in the Favorites menu), keeps
            // the click pressed, moves the cursor outside the dropdown and releases the click
            // (i.e. mousedown and focus inside the item, mouseup and click outside the dropdown).
            // In this case, we want to keep the dropdown menu open.
            assert.expect(5);

            const items = this.items;
            class Parent extends owl.Component {
                constructor() {
                    super(...arguments);
                    this.items = items;
                }
            }
            Parent.components = { DropdownMenu };
            Parent.template = owl.tags.xml`
                <div>
                    <DropdownMenu class="first" title="'First'" items="items"/>
                </div>`;
            const parent = new Parent();
            await parent.mount(testUtils.prepareTarget(), { position: "first-child" });

            const menu = parent.el.querySelector(".dropdown");
            assert.doesNotHaveClass(menu, "show", "dropdown should not be open");

            await testUtils.dom.click(menu.querySelector("button"));
            assert.hasClass(menu, "show", "dropdown should be open");

            const firstItemEl = menu.querySelector(".o_menu_item > a");
            // open options menu
            await testUtils.dom.click(firstItemEl);
            assert.hasClass(firstItemEl.querySelector("i"), "o_icon_right fa fa-caret-down");

            // force the focus inside the dropdown item and click outside
            firstItemEl.parentElement.querySelector(".o_menu_item_options .o_item_option a").focus();
            await testUtils.dom.triggerEvents(parent.el, "click");
            assert.hasClass(menu, "show", "dropdown should still be open");
            assert.hasClass(firstItemEl.querySelector("i"), "o_icon_right fa fa-caret-down");

            parent.destroy();
        });
    });
});
