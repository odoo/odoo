/** @odoo-module **/
    
    import DropdownMenu from "web.DropdownMenu";
    import testUtils from "web.test_utils";

    const { createComponent } = testUtils;

    QUnit.module('Components', {
        before: function () {
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

        QUnit.test('display dropdown at the right position', async function (assert) {
            assert.expect(2);
            const viewPort = testUtils.prepareTarget();
            viewPort.style.position = 'initial';

            const dropdown = await createComponent(DropdownMenu, {
                env: {
                    device: {
                        isMobile: true
                    },
                },
                props: {
                    items: this.items,
                    title: "Dropdown",
                },
            });

            await testUtils.dom.click(dropdown.el.querySelector('button'));
            assert.containsOnce(dropdown.el, '.dropdown-menu-start',
                "should display the dropdown menu at the right screen");
            await testUtils.dom.click(dropdown.el.querySelector('button'));

            // position the dropdown to the right
            dropdown.el.parentNode.classList.add('clearfix');
            dropdown.el.classList.add('float-end');
            await testUtils.dom.click(dropdown.el.querySelector('button'));
            assert.containsOnce(dropdown.el, '.dropdown-menu-end',
                "should display the dropdown menu at the left screen");

            dropdown.el.parentNode.classList.remove('clearfix');
            viewPort.style.position = '';

        });
    });
