odoo.define('point_of_sale.tests.ProductScreen', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');
    const testUtils = require('web.test_utils');
    const makePosTestEnv = require('point_of_sale.test_env');
    const { xml } = owl.tags;
    const { useState } = owl;

    QUnit.module('unit tests for ProductScreen components', {});

    QUnit.test('ActionpadWidget', async function (assert) {
        assert.expect(7);

        class Parent extends PosComponent {
            constructor() {
                super();
                useListener('click-customer', () => assert.step('click-customer'));
                useListener('click-pay', () => assert.step('click-pay'));
                this.state = useState({ client: null });
            }
        }
        Parent.env = makePosTestEnv();
        Parent.template = xml/* html */ `
            <div>
                <ActionpadWidget client="state.client" />
            </div>
        `;

        const parent = new Parent();
        await parent.mount(testUtils.prepareTarget());

        const setCustomerButton = parent.el.querySelector('button.set-customer');
        const payButton = parent.el.querySelector('button.pay');

        await testUtils.nextTick();
        assert.ok(setCustomerButton.innerText.includes('Customer'));

        // change to customer with short name
        parent.state.client = { name: 'Test' };
        await testUtils.nextTick();
        assert.ok(setCustomerButton.innerText.includes('Test'));

        // change to customer with long name
        parent.state.client = { name: 'Change Customer' };
        await testUtils.nextTick();
        assert.ok(setCustomerButton.classList.contains('decentered'));

        parent.state.client = null;

        // click set-customer button
        await testUtils.dom.click(setCustomerButton);
        await testUtils.nextTick();
        assert.verifySteps(['click-customer']);

        // click pay button
        await testUtils.dom.click(payButton);
        await testUtils.nextTick();
        assert.verifySteps(['click-pay']);

        parent.unmount();
        parent.destroy();
    });

    QUnit.test('NumpadWidget', async function (assert) {
        assert.expect(25);

        class Parent extends PosComponent {
            constructor() {
                super(...arguments);
                useListener('set-numpad-mode', this.setNumpadMode);
                useListener('numpad-click-input', this.numpadClickInput);
                this.state = useState({ mode: 'quantity' });
            }
            setNumpadMode({ detail: { mode } }) {
                this.state.mode = mode;
                assert.step(mode);
            }
            numpadClickInput({ detail: { key } }) {
                assert.step(key);
            }
        }
        Parent.env = makePosTestEnv();
        Parent.template = xml/* html */ `
            <div><NumpadWidget activeMode="state.mode"></NumpadWidget></div>
        `;

        const pos = Parent.env.pos;
        // set this old values back after testing
        const old_config = pos.config;
        const old_cashier = pos.get('cashier');

        // set dummy values in pos.config and pos.get('cashier')
        pos.config = {
            restrict_price_control: false,
            manual_discount: true
        };
        pos.set('cashier', { role: 'manager' });

        const parent = new Parent();
        await parent.mount(testUtils.prepareTarget());

        const modeButtons = parent.el.querySelectorAll('.mode-button');
        let qtyButton, discButton, priceButton;
        for (let button of modeButtons) {
            if (button.textContent.includes('Qty')) {
                qtyButton = button;
            }
            if (button.textContent.includes('Disc')) {
                discButton = button;
            }
            if (button.textContent.includes('Price')) {
                priceButton = button;
            }
        }

        // initially, qty button is active
        assert.ok(qtyButton.classList.contains('selected-mode'));
        assert.ok(!discButton.classList.contains('selected-mode'));
        assert.ok(!priceButton.classList.contains('selected-mode'));

        await testUtils.dom.click(discButton);
        await testUtils.nextTick();
        assert.ok(!qtyButton.classList.contains('selected-mode'));
        assert.ok(discButton.classList.contains('selected-mode'));
        assert.ok(!priceButton.classList.contains('selected-mode'));
        assert.verifySteps(['discount']);

        await testUtils.dom.click(priceButton);
        await testUtils.nextTick();
        assert.ok(!qtyButton.classList.contains('selected-mode'));
        assert.ok(!discButton.classList.contains('selected-mode'));
        assert.ok(priceButton.classList.contains('selected-mode'));
        assert.verifySteps(['price']);

        const numpadOne = [...parent.el.querySelectorAll('.number-char').values()].find((el) =>
            el.textContent.includes('1')
        );
        const numpadMinus = parent.el.querySelector('.numpad-minus');
        const numpadBackspace = parent.el.querySelector('.numpad-backspace');

        await testUtils.dom.click(numpadOne);
        await testUtils.nextTick();
        assert.verifySteps(['1']);

        await testUtils.dom.click(numpadMinus);
        await testUtils.nextTick();
        assert.verifySteps(['-']);

        await testUtils.dom.click(numpadBackspace);
        await testUtils.nextTick();
        assert.verifySteps(['Backspace']);

        await testUtils.dom.click(priceButton);
        await testUtils.nextTick();
        assert.verifySteps(['price']);

        // change to price control restriction and the cashier is not manager
        pos.config.restrict_price_control = true;
        pos.set('cashier', { role: 'not manager' });
        await testUtils.nextTick();

        assert.ok(priceButton.classList.contains('disabled-mode'));
        assert.ok(qtyButton.classList.contains('selected-mode'));
        // after the cashier is changed, since it is not a manager,
        // the 'set-numpad-mode' is triggered, setting the mode to
        // 'quantity'.
        assert.verifySteps(['quantity']);

        // reset old config and cashier values to pos
        pos.config = old_config;
        pos.set('cashier', old_cashier);

        parent.unmount();
        parent.destroy();
    });

    QUnit.test('ProductsWidgetControlPanel', async function (assert) {
        assert.expect(32);

        // This test incorporates the following components:
        // CategoryBreadcrumb
        // CategoryButton
        // CategorySimpleButton
        // HomeCategoryBreadcrumb

        // Create dummy category data
        //
        // Root
        //   | Test1
        //   |   | Test2
        //   |   ` Test3
        //   |       | Test5
        //   |       ` Test6
        //   ` Test4

        const rootCategory = { id: 0, name: 'Root', parent: null };
        const testCategory1 = { id: 1, name: 'Test1', parent: 0 };
        const testCategory2 = { id: 2, name: 'Test2', parent: 1 };
        const testCategory3 = { id: 3, name: 'Test3', parent: 1 };
        const testCategory4 = { id: 4, name: 'Test4', parent: 0 };
        const testCategory5 = { id: 5, name: 'Test5', parent: 3 };
        const testCategory6 = { id: 6, name: 'Test6', parent: 3 };
        const categories = {
            0: rootCategory,
            1: testCategory1,
            2: testCategory2,
            3: testCategory3,
            4: testCategory4,
            5: testCategory5,
            6: testCategory6,
        };

        class Parent extends PosComponent {
            constructor() {
                super(...arguments);
                this.state = useState({ selectedCategoryId: 0 });
                useListener('switch-category', this.switchCategory);
                useListener('update-search', this.updateSearch);
                useListener('clear-search', this.clearSearch);
            }
            get breadcrumbs() {
                if (this.state.selectedCategoryId === 0) return [];
                let current = categories[this.state.selectedCategoryId];
                const res = [current];
                while (current.parent != 0) {
                    const toAdd = categories[current.parent];
                    res.push(toAdd);
                    current = toAdd;
                }
                return res.reverse();
            }
            get subcategories() {
                return Object.values(categories).filter(
                    ({ parent }) => parent == this.state.selectedCategoryId
                );
            }
            switchCategory({ detail: id }) {
                this.state.selectedCategoryId = id;
                assert.step(`${id}`);
            }
            updateSearch(event) {
                assert.step(event.detail);
            }
            clearSearch() {
                assert.step('cleared');
            }
        }
        Parent.env = makePosTestEnv();
        Parent.template = xml/* html */ `
            <div class="pos">
                <div class="search-bar-portal">
                    <ProductsWidgetControlPanel breadcrumbs="breadcrumbs" subcategories="subcategories" />
                </div>
            </div>
        `;

        const pos = Parent.env.pos;
        const old_config = pos.config;
        // set dummy config
        pos.config = { iface_display_categ_images: false };

        const parent = new Parent();
        await parent.mount(testUtils.prepareTarget());

        // The following tests the breadcrumbs and subcategory buttons

        // check if HomeCategoryBreadcrumb is rendered
        assert.ok(
            parent.el.querySelector('.breadcrumb-home'),
            'Home category should always be there'
        );
        let subcategorySpans = [...parent.el.querySelectorAll('.category-simple-button')];
        assert.ok(subcategorySpans.length === 2, 'There should be 2 subcategories for Root.');
        assert.ok(subcategorySpans.find((span) => span.textContent.includes('Test1')));
        assert.ok(subcategorySpans.find((span) => span.textContent.includes('Test4')));

        // click Test1
        let test1Span = subcategorySpans.find((span) => span.textContent.includes('Test1'));
        await testUtils.dom.click(test1Span);
        await testUtils.nextTick();
        assert.verifySteps(['1']);
        assert.ok(
            [...parent.el.querySelectorAll('.breadcrumb-button')][1].textContent.includes('Test1')
        );
        subcategorySpans = [...parent.el.querySelectorAll('.category-simple-button')];
        assert.ok(subcategorySpans.length === 2, 'There should be 2 subcategories for Root.');
        assert.ok(subcategorySpans.find((span) => span.textContent.includes('Test2')));
        assert.ok(subcategorySpans.find((span) => span.textContent.includes('Test3')));

        // click Test2
        let test2Span = subcategorySpans.find((span) => span.textContent.includes('Test2'));
        await testUtils.dom.click(test2Span);
        await testUtils.nextTick();
        assert.verifySteps(['2']);
        subcategorySpans = [...parent.el.querySelectorAll('.category-simple-button')];
        assert.ok(subcategorySpans.length === 0, 'Test2 should not have subcategories');

        // go back to Test1
        let breadcrumb1 = [...parent.el.querySelectorAll('.breadcrumb-button')].find((el) =>
            el.textContent.includes('Test1')
        );
        await testUtils.dom.click(breadcrumb1);
        await testUtils.nextTick();
        assert.verifySteps(['1']);

        // click Test3
        subcategorySpans = [...parent.el.querySelectorAll('.category-simple-button')];
        let test3Span = subcategorySpans.find((span) => span.textContent.includes('Test3'));
        await testUtils.dom.click(test3Span);
        await testUtils.nextTick();
        assert.verifySteps(['3']);
        subcategorySpans = [...parent.el.querySelectorAll('.category-simple-button')];
        assert.ok(subcategorySpans.length === 2);

        // click Test6
        let test6Span = subcategorySpans.find((span) => span.textContent.includes('Test6'));
        await testUtils.dom.click(test6Span);
        await testUtils.nextTick();
        assert.verifySteps(['6']);
        let breadcrumbButtons = [...parent.el.querySelectorAll('.breadcrumb-button')];
        assert.ok(breadcrumbButtons.length === 4);

        // Now check subcategory buttons with images
        pos.config.iface_display_categ_images = true;

        let breadcrumbHome = parent.el.querySelector('.breadcrumb-home');
        await testUtils.dom.click(breadcrumbHome);
        await testUtils.nextTick();
        assert.verifySteps(['0']);
        assert.ok(
            !parent.el.querySelector('.category-list').classList.contains('simple'),
            'Category list should not have simple class'
        );
        let categoryButtons = [...parent.el.querySelectorAll('.category-button')];
        assert.ok(categoryButtons.length === 2, 'There should be 2 subcategories for Root');

        // The following tests the search bar

        const wait = (ms) => {
            return new Promise((resolve) => {
                setTimeout(resolve, ms);
            });
        };

        const inputEl = parent.el.querySelector('.search-box input');
        await testUtils.dom.triggerEvent(inputEl, 'keyup', { key: 'A' });
        // Triggering keyup event doesn't type the key to the input
        // so we manually assign the value of the input.
        inputEl.value = 'A';
        await wait(30);
        await testUtils.dom.triggerEvent(inputEl, 'keyup', { key: 'B' });
        inputEl.value = 'AB';
        await wait(30);
        await testUtils.dom.triggerEvent(inputEl, 'keyup', { key: 'C' });
        inputEl.value = 'ABC';
        await wait(110);
        // Only after waiting for more than 100ms that update-search is triggered
        // because the method is debounced.
        assert.verifySteps(['ABC']);
        await testUtils.dom.triggerEvent(inputEl, 'keyup', { key: 'D' });
        inputEl.value = 'ABCD';
        await wait(110);
        assert.verifySteps(['ABCD']);

        // clear the search bar
        await testUtils.dom.click(parent.el.querySelector('.search-box .clear-icon'));
        await testUtils.nextTick();
        assert.verifySteps(['cleared']);
        assert.ok(inputEl.value === '', 'value of the input element should be empty');

        pos.config = old_config;

        parent.unmount();
        parent.destroy();
    });

    QUnit.test('ProductList, ProductItem', async function (assert) {
        assert.expect(10);

        // patch imageUrl and price of ProductItem component
        const MockProductItemExt = (X) =>
            class extends X {
                get imageUrl() {
                    return 'data:,';
                }
                get price() {
                    return this.props.product.price;
                }
            };

        const extension = Registries.Component.extend('ProductItem', MockProductItemExt);
        extension.compile();

        const dummyProducts = [
            { id: 0, display_name: 'Burger', price: '$10' },
            { id: 1, display_name: 'Water', price: '$2' },
            { id: 2, display_name: 'Chair', price: '$25' },
        ];

        class Parent extends PosComponent {
            constructor() {
                super(...arguments);
                this.state = useState({ searchWord: '', products: dummyProducts });
                useListener('click-product', this._clickProduct);
            }
            _clickProduct({ detail: product }) {
                assert.step(product.display_name);
            }
        }
        Parent.env = makePosTestEnv();
        Parent.template = xml/* html */ `
            <div>
                <ProductList products="state.products" searchWord="state.searchWord" />
            </div>
        `;

        const parent = new Parent();
        await parent.mount(testUtils.prepareTarget());

        // Check if there are 3 products listed
        assert.strictEqual(
            parent.el.querySelectorAll('article.product').length,
            3,
            'There should be 3 products listed'
        );

        // Check contents of product item and click
        const product1el = parent.el.querySelector(
            'article.product[aria-labelledby="article_product_1"]'
        );
        assert.ok(product1el.querySelector('.product-img img[data-alt="Water"]'));
        assert.ok(product1el.querySelector('.product-img .price-tag').textContent.includes('$2'));
        await testUtils.dom.click(product1el);
        await testUtils.nextTick();
        assert.verifySteps(['Water']);

        // Remove one product, check if only two is listed
        parent.state.products.splice(0, 1);
        await testUtils.nextTick();
        assert.strictEqual(
            parent.el.querySelectorAll('article.product').length,
            2,
            'There should be 2 products listed after removing the first item'
        );

        // Remove all products, check if empty message is There are no products in this category
        parent.state.products.splice(0, parent.state.products.length);
        await testUtils.nextTick();
        assert.strictEqual(
            parent.el.querySelectorAll('article.product').length,
            0,
            'There should be 0 products listed after removing everything'
        );
        assert.ok(
            parent.el
                .querySelector('.product-list-empty p')
                .textContent.includes('There are no products in this category.')
        );

        // change the searchWord to 'something', check if empty message is No results found
        parent.state.searchWord = 'something';
        await testUtils.nextTick();
        assert.ok(
            parent.el
                .querySelector('.product-list-empty p')
                .textContent.includes('No results found for')
        );
        assert.ok(
            parent.el.querySelector('.product-list-empty p b').textContent.includes('something')
        );

        extension.remove();

        parent.unmount();
        parent.destroy();
    });

    QUnit.test('Orderline', async function (assert) {
        assert.expect(10);

        class Parent extends PosComponent {
            constructor(product) {
                super();
                useListener('select-line', this._selectLine);
                useListener('edit-pack-lot-lines', this._editPackLotLines);
                this.order.add_product(product);
            }
            get order() {
                return this.env.pos.get_order();
            }
            get line() {
                return this.env.pos.get_order().get_orderlines()[0];
            }
            _selectLine() {
                assert.step('select-line');
            }
            _editPackLotLines() {
                assert.step('edit-pack-lot-lines');
            }
            willUnmount() {
                this.order.remove_orderline(this.line);
            }
        }
        Parent.env = makePosTestEnv();
        Parent.template = xml/* html */ `
            <div>
                <Orderline line="line" />
            </div>
        `;

        const [chair1, chair2] = Parent.env.pos.db.search_product_in_category(0, 'Office Chair');
        // patch chair2 to have tracking
        chair2.tracking = 'serial';

        // 1. Test orderline without lot icon

        let parent = new Parent(chair1);
        await parent.mount(testUtils.prepareTarget());

        let line = parent.el.querySelector('li.orderline');
        assert.ok(line);
        assert.notOk(line.querySelector('.line-lot-icon'), 'there should be no lot icon');
        await testUtils.dom.click(line);
        assert.verifySteps(['select-line']);

        parent.unmount();
        parent.destroy();

        // 2. Test orderline with lot icon

        parent = new Parent(chair2);
        await parent.mount(testUtils.prepareTarget());

        line = parent.el.querySelector('li.orderline');
        const lotIcon = line.querySelector('.line-lot-icon');
        assert.ok(line);
        assert.ok(lotIcon, 'there should be lot icon');
        await testUtils.dom.click(line);
        assert.verifySteps(['select-line']);
        await testUtils.dom.click(lotIcon);
        assert.verifySteps(['edit-pack-lot-lines']);

        parent.unmount();
        parent.destroy();
    });

    QUnit.test('OrderWidget', async function (assert) {
        assert.expect(8);

        // OrderWidget is dependent on its parent's rerendering
        class Parent extends PosComponent {
            mounted() {
                this.env.pos.on('change:selectedOrder', this.render, this);
            }
            willUnmount() {
                this.env.pos.off('change:selectedOrder', null, this);
            }
        }
        Parent.env = makePosTestEnv();
        Parent.template = xml/* html */ `
            <div>
                <OrderWidget />
            </div>
        `;

        const [chair1, chair2] = Parent.env.pos.db.search_product_in_category(0, 'Office Chair');

        let parent = new Parent();
        await parent.mount(testUtils.prepareTarget());

        // current order is empty
        assert.notOk(parent.el.querySelector('.summary'));
        assert.ok(parent.el.querySelector('.order-empty'));

        // add line to the current order
        const order1 = parent.env.pos.get_order();
        order1.add_product(chair1);
        await testUtils.nextTick();
        assert.ok(parent.el.querySelector('.summary'));
        assert.notOk(parent.el.querySelector('.order-empty'));

        // selected new order, new order is empty
        const order2 = parent.env.pos.add_new_order();
        await testUtils.nextTick();
        assert.notOk(parent.el.querySelector('.summary'));
        assert.ok(parent.el.querySelector('.order-empty'));

        // add line to the current order
        order2.add_product(chair2);
        await testUtils.nextTick();
        assert.ok(parent.el.querySelector('.summary'));
        assert.notOk(parent.el.querySelector('.order-empty'));

        parent.env.pos.delete_current_order();
        parent.env.pos.delete_current_order();

        parent.unmount();
        parent.destroy();
    });
});
