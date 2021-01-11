odoo.define('mail/static/src/component_hooks/use_store/use_store_tests.js', function (require) {
'use strict';

const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');
const {
    afterNextRender,
    nextAnimationFrame,
} = require('mail/static/src/utils/test_utils.js');

const { Component, QWeb, Store } = owl;
const { onPatched, useGetters } = owl.hooks;
const { xml } = owl.tags;

QUnit.module('mail', {}, function () {
QUnit.module('component_hooks', {}, function () {
QUnit.module('use_store', {}, function () {
QUnit.module('use_store_tests.js', {
    beforeEach() {
        const qweb = new QWeb();
        this.env = { qweb };
    },
    afterEach() {
        this.env = undefined;
        this.store = undefined;
    },
});


QUnit.test("compare keys, no depth, primitives", async function (assert) {
    assert.expect(8);
    this.store = new Store({
        env: this.env,
        getters: {
            get({ state }, key) {
                return state[key];
            },
        },
        state: {
            obj: {
                subObj1: 'a',
                subObj2: 'b',
                use1: true,
            },
        },
    });
    this.env.store = this.store;
    let count = 0;
    class MyComponent extends Component {
        constructor() {
            super(...arguments);
            this.storeGetters = useGetters();
            this.storeProps = useStore(props => {
                const obj = this.storeGetters.get('obj');
                return {
                    res: obj.use1 ? obj.subObj1 : obj.subObj2,
                };
            });
            onPatched(() => {
                count++;
            });
        }
    }
    Object.assign(MyComponent, {
        env: this.env,
        props: {},
        template: xml`<div t-esc="storeProps.res"/>`,
    });

    const fixture = document.querySelector('#qunit-fixture');

    const myComponent = new MyComponent();
    await myComponent.mount(fixture);
    assert.strictEqual(count, 0,
        'should not detect an update initially');
    assert.strictEqual(fixture.textContent, 'a',
        'should display the content of subObj1');

    await afterNextRender(() => {
        this.store.state.obj.use1 = false;
    });
    assert.strictEqual(count, 1,
        'should detect an update because the selector is returning a different value (was subObj1, now is subObj2)');
    assert.strictEqual(fixture.textContent, 'b',
        'should display the content of subObj2');

    this.store.state.obj.subObj2 = 'b';
    // there must be no render here
    await nextAnimationFrame();
    assert.strictEqual(count, 1,
        'should not detect an update because the same primitive value was assigned (subObj2 was already "b")');
    assert.strictEqual(fixture.textContent, 'b',
        'should still display the content of subObj2');

    await afterNextRender(() => {
        this.store.state.obj.subObj2 = 'd';
    });
    assert.strictEqual(count, 2,
        'should detect an update because the selector is returning a different value for subObj2');
    assert.strictEqual(fixture.textContent, 'd',
        'should display the new content of subObj2');

    myComponent.destroy();
});

QUnit.test("compare keys, depth 1, proxy", async function (assert) {
    assert.expect(8);
    this.store = new Store({
        env: this.env,
        getters: {
            get({ state }, key) {
                return state[key];
            },
        },
        state: {
            obj: {
                subObj1: { a: 'a' },
                subObj2: { a: 'b' },
                use1: true,
            },
        },
    });
    this.env.store = this.store;
    let count = 0;
    class MyComponent extends Component {
        constructor() {
            super(...arguments);
            this.storeGetters = useGetters();
            this.storeProps = useStore(props => {
                const obj = this.storeGetters.get('obj');
                return {
                    array: [obj.use1 ? obj.subObj1 : obj.subObj2],
                };
            }, {
                compareDepth: {
                    array: 1,
                },
            });
            onPatched(() => {
                count++;
            });
        }
    }
    Object.assign(MyComponent, {
        env: this.env,
        props: {},
        template: xml`<div t-esc="storeProps.array[0].a"/>`,
    });

    const fixture = document.querySelector('#qunit-fixture');

    const myComponent = new MyComponent();
    await myComponent.mount(fixture);
    assert.strictEqual(count, 0,
        'should not detect an update initially');
    assert.strictEqual(fixture.textContent, 'a',
        'should display the content of subObj1');

    await afterNextRender(() => {
        this.store.state.obj.use1 = false;
    });
    assert.strictEqual(count, 1,
        'should detect an update because the selector is returning a different value (was subObj1, now is subObj2)');
    assert.strictEqual(fixture.textContent, 'b',
        'should display the content of subObj2');

    this.store.state.obj.subObj1.a = 'c';
    // there must be no render here
    await nextAnimationFrame();
    assert.strictEqual(count, 1,
        'should not detect an update because subObj1 was changed but only subObj2 is selected');
    assert.strictEqual(fixture.textContent, 'b',
        'should still display the content of subObj2');

    await afterNextRender(() => {
        this.store.state.obj.subObj2.a = 'd';
    });
    assert.strictEqual(count, 2,
        'should detect an update because the value of subObj2 changed');
    assert.strictEqual(fixture.textContent, 'd',
        'should display the new content of subObj2');

    myComponent.destroy();
});

});
});
});

});
