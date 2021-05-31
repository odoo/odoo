# Testing

We take very seriously code quality. Tests is an important part of a solid and
robust application. Each feature should be (if reasonable) tested properly, in
the QUnit test suite (available in the route `/wowl/tests`)

In a few sentences, here is how the test suite is organized:

-   tests are written in the `static/tests` folder.
-   the main entry point for the suite is `static/tests/main.ts`, which is the
    code that setup the test suite environment.
-   some helpers are available in `static/tests/helpers.ts`.
-   to access the test suite, one needs to have an odoo server running and then
    open `/wowl/tests` in a browser

The test suite file structure looks like this:

```
static/
  ...
  tests/
    components/
      navbar_tests.ts
      ...
    services/
      router_tests.ts
      ...
    helpers.ts    <-- helpers that will probably be imported in each test file
    main.ts       <-- main file, used to generate the test bundle
    qunit.ts      <-- qunit config file. No test should import this
```

## Test helpers

-   `mount(SomeComponent, {env, target})`: create a component with the `env` provided,
    and mount it to the `target` html element. This method is asynchronous, and
    returns the instance of the component

-   `makeTestEnv(params?: Params)`: create asynchronously a test environment. By default, a test
    environment has no service, components or browser access. It can be optionally
    customized with the `params` argument:

    -   `services (optional, Registry<Service>)`: a registry of services
    -   `Components (optional, Registry<Component>)`) main component registry
    -   `browser (optional, object)`: the browser object that will be used for the
        test environment.

-   `getFixture(): HTMLElement`: return an html element to use as a DOM node for tests (only
    applies to code that needs to interact with the DOM, obviously).

-   `nextTick(): Promise<void>`: helper to wait for the next animation frame. This
    is extremely useful while writing tests involving components updating the DOM.

-   `click(el: HTMLElement, selector?: string): Promise<void>`: helper to click on
    an element, given the element itself, or an element and a selector that matches
    a single element inside it. The helper will crash when called with a selector
    that have no match, or more than 1 match. It returns a promise resolved after
    the next animation frame, i.e. after potential DOM updates have been applied.

## QUnit custom assertions

QUnit provides several [built-in assertions](https://api.qunitjs.com/assert/),
available on the `QUnit.assert` object. Alongside them, we provide custom
assertions.

-   `assert.containsN(el: HTMLElement, selector: string, n: number, msg?: string)`:
    check that a target element `el` contains exactly `n` matches for the given
    `selector`, with `msg` being an optional short description of the assertion

-   `assert.containsNone(el: HTMLElement, selector: string, msg?: string)`: check
    that a target element `el` contains no match for the given `selector`

-   `assert.containsOnce(el: HTMLElement, selector: string, msg?: string)`: check
    that a target element `el` contains exactly one match for the given `selector`

-   `assert.hasClass(el: HTMLElement, classNames: string, msg?: string)`: check
    that a target element `el` has the given `classNames`

-   `assert.doesNotHaveClass(el: HTMLElement, classNames: string, msg?: string)`: check
    that a target element `el` does not have the given `classNames`.

## Adding a new test

To add a new test file to the QUnit suite, the following steps need to be done:

1. create a new file named `something_test.ts` in the `static/tests` folder
2. import your file in `static/tests/main.ts` (so it will be added to the test bundle)
3. add your tests inside your new file.

Here is a simple example of a test file to test a component:

```ts
import * as QUnit from "qunit";
import { MyComponent } from "../../src/components/...";
import { getFixture, makeTestEnv, mount, OdooEnv } from "../helpers";

let target: HTMLElement;
let env: OdooEnv;
QUnit.module("MyComponent", {
    beforeEach() {
        target = getFixture();
        env = makeTestEnv();
    }
});

QUnit.test("can be rendered", async (assert) => {
    assert.expect(1);
    const myComponent = await mount(MyComponent, { env, target });
    // perform some assertion/actions
});
```

## Debugging a test

Sometimes, changes in the code make tests fail. Understanding why assertions
fail reading the logs might be tedious. Hopefully, one can use our custom
`QUnit.debug` function instead of `QUnit.test` (basically, rename `ŧest` into
`debug` for the failing test). With this, the target returned by `getFixture`
will be `document.body`, so that what has been inserted into the DOM is visible,
and can be directly interacted with.
