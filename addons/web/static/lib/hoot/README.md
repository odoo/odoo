<header>
    <h1>HOOT</h1>
    <strong>H</strong>ierarchically <strong>O</strong>rganized <strong>O</strong>doo <strong>T</strong>ests
</header>

## Get started

### Main API

- describe

- expect

- start

- test

### Hooks

- after

- afterAll

- afterEach

- before

- beforeAll

- beforeEach

- onError

### Other functions

- dryRun

- getCurrent


## Matchers

### 1. toBe

Expects the received value to be strictly equal to the `expected` value.

- Arguments
    * `expected`: any
    * `options`: ExpectOptions

- Examples

    ```js
    expect("foo").toBe("foo");

    expect({ foo: 1 }).not.toBe({ foo: 1 });
    ```


### 2. toBeEmpty

Expects the received value to be empty: - `iterable`: no items - `object`: no keys - `node`: no content (i.e. no value or text) - anything else: falsy value (`false`, `0`, `""`, `null`, `undefined`)

- Arguments
    * `options`: ExpectOptions

- Examples

    ```js
    expect({}).toBeEmpty();

    expect(["a", "b"]).not.toBeEmpty();

    expect(queryOne("input")).toBeEmpty();
    ```


### 3. toBeGreaterThan

Expects the received value to be strictly greater than `max`.

- Arguments
    * `max`: number
    * `options`: ExpectOptions

- Examples

    ```js
    expect(5).toBeGreaterThan(-1);

    expect(4 + 2).toBeGreaterThan(5);
    ```


### 4. toBeLessThan

Expects the received value to be strictly less than `min`.

- Arguments
    * `min`: number
    * `options`: ExpectOptions

- Examples

    ```js
    expect(5).toBeLessThan(10);

    expect(8 - 6).toBeLessThan(3);
    ```


### 5. toBeOfType

Expects the received value to be of the given type.

- Arguments
    * `type`: ArgumentType
    * `options`: ExpectOptions

- Examples

    ```js
    expect("foo").toBeOfType("");

    expect({ foo: 1 }).toBeOfType("object");
    ```


### 6. toBeTruthy

Expects the received value to resolve to a truthy expression.

- Arguments
    * `options`: ExpectOptions

- Examples

    ```js
    expect(true).toBeTruthy();

    expect([]).toBeTruthy();
    ```


### 7. toBeWithin

Expects the received value to be strictly between `min` (inclusive) and `max` (exclusive).

- Arguments
    * `min (inclusive)`: number
    * `max (exlusive)`: number
    * `options`: ExpectOptions

- Examples

    ```js
    expect(3).toBeWithin(3, 9);

    expect(-8).toBeWithin(-20, 0);

    expect(100).not.toBeWithin(50, 100);
    ```


### 8. toEqual

Expects the received value to be deeply equal to the `expected` value.

- Arguments
    * `expected`: any
    * `options`: ExpectOptions

- Examples

    ```js
    expect(["foo"]).toEqual(["foo"]);

    expect({ foo: 1 }).toEqual({ foo: 1 });
    ```


### 9. toMatch

Expects the received value to match the given matcher (string or RegExp).

- Arguments
    * `matcher`: import("../utils").Matcher
    * `options`: ExpectOptions

- Examples

    ```js
    expect(new Error("foo")).toMatch("foo");

    expect("a foo value").toMatch(/fo.*ue/);
    ```


### 10. toSatisfy

Expects the received value to satisfy the given predicate, taking the received value as argument.

- Arguments
    * `predicate`: (received: any) => boolean
    * `options`: ExpectOptions

- Examples

    ```js
    expect("foo").toSatisfy((value) => typeof value === "string");

    expect(false).not.toSatisfy(Boolean);
    ```


### 11. toThrow

Expects the received value (`Function`) to throw an error after being called.

- Arguments
    * `matcher`: Matcher
    * `options`: ExpectOptions

- Examples

    ```js
    expect(() => { throw new Error("Woops!") }).toThrow(/woops/i);

    await expect(Promise.reject("foo")).rejects.toThrow("foo");
    ```


### 12. toVerifyErrors

Expects the received matchers to match the errors thrown since the start of the test or the last call to {@link toVerifyErrors}. Calling this matcher will reset the list of current errors.

- Arguments
    * `options`: ExpectOptions

- Examples

    ```js
    expect([/RPCError/, /Invalid domain AST/]).toVerifyErrors();
    ```


### 13. toVerifySteps

Expects the received steps to be equal to the steps emitted since the start of the test or the last call to {@link toVerifySteps}. Calling this matcher will reset the list of current steps.

- Arguments
    * `options`: ExpectOptions

- Examples

    ```js
    expect(["web_read_group", "web_search_read"]).toVerifySteps();
    ```


### 14. toBeChecked

Expects the received {@link Target} to be checked, or to be indeterminate if the homonymous option is set to `true`.

- Arguments
    * `options`: ExpectOptions & { indeterminate?: boolean }

- Examples

    ```js
    expect("input[type=checkbox]").toBeChecked();
    ```


### 15. toBeDisplayed

Expects the received {@link Target} to be displayed, meaning that: - it has a bounding box; - it is contained in the root document.

- Arguments
    * `options`: ExpectOptions

- Examples

    ```js
    expect(document.body).toBeDisplayed();

    expect(document.createElement("div")).not.toBeDisplayed();
    ```


### 16. toBeEnabled

Expects the received {@link Target} to be enabled, meaning that it matches the `:enabled` pseudo-selector.

- Arguments
    * `options`: ExpectOptions

- Examples

    ```js
    expect("button").toBeEnabled();

    expect("input[type=radio]").not.toBeEnabled();
    ```


### 17. toBeFocused

Expects the received {@link Target} to be focused in its owner document.

- Arguments
    * `options`: ExpectOptions


### 18. toBeVisible

Expects the received {@link Target} to be visible, meaning that: - it has a bounding box; - it is contained in the root document; - it is not hidden by CSS properties.

- Arguments
    * `options`: ExpectOptions

- Examples

    ```js
    expect(document.body).toBeVisible();

    expect("[style='opacity: 0']").not.toBeVisible();
    ```


### 19. toContain

Expects the received {@link Target} to contain the given {@link Target}.

- Arguments
    * `target`: Target
    * `options`: ExpectOptions

- Examples

    ```js
    expect("ul").toContain(queryOne("li"));
    ```


### 20. toHaveAttribute

Expects the received {@link Target} to have the given attribute set on itself, and for that attribute value to match the given `value` if any.

- Arguments
    * `attribute`: string
    * `value`: string
    * `options`: ExpectOptions

- Examples

    ```js
    expect("a").toHaveAttribute("href");

    expect("script").toHaveAttribute("src", "./index.js");
    ```


### 21. toHaveClass

Expects the received {@link Target} to have the given class name(s).

- Arguments
    * `className`: string | string[]
    * `options`: ExpectOptions

- Examples

    ```js
    expect("button").toHaveClass("btn");

    expect("body").toHaveClass(["o_webclient", "o_dark"]);
    ```


### 22. toHaveCount

Expects the received {@link Target} to contain a certain `amount` of elements: - {@link Number}: exactly `<amount>` element(s) - {@link false}: any amount of matching elements Note that the `amount` parameter can be omitted, in which case it will be implicitly resolved as `false` (= any).

- Arguments
    * `amount`: number | false
    * `options`: ExpectOptions

- Examples

    ```js
    expect(".o_webclient").toHaveCount(1);

    expect(".o_form_view .o_field_widget").toHaveCount();

    expect("ul > li").toHaveCount(4);
    ```


### 23. toHaveProperty

Expects the received {@link Target} to have the given attribute set on itself, and for that attribute value to match the given `value` if any.

- Arguments
    * `property`: string
    * `value`: string
    * `options`: ExpectOptions

- Examples

    ```js
    expect("button").toHaveProperty("tabIndex", 0);

    expect("script").toHaveProperty("src", "./index.js");
    ```


### 24. toHaveStyle

Expects the received {@link Target} to have the given class name(s).

- Arguments
    * `style`: string | string[]
    * `options`: ExpectOptions

- Examples

    ```js
    expect("button").toHaveStyle({ color: "red" });

    expect("p").toHaveStyle("text-align: center");
    ```


### 25. toHaveText

Expects the text content of the received {@link Target} to either: - be strictly equal to a given string, - match a given regular expression;

- Arguments
    * `text`: string | RegExp
    * `options`: ExpectOptions

- Examples

    ```js
    expect("p").toHaveText("lorem ipsum dolor sit amet");

    expect("header h1").toHaveText(/odoo/i);
    ```


### 26. toHaveValue

Expects the value of the received {@link Target} to either: - be strictly equal to a given string or number, - match a given regular expression, - contain file objects matching the given `files` list;

- Arguments
    * `value`: ReturnType<typeof getNodeValue>
    * `options`: ExpectOptions

- Examples

    ```js
    expect("input[type=email]").toHaveValue("john@doe.com");

    expect("input[type=file]").toHaveValue(new File(["foo"], "foo.txt"));

    expect("select[multiple]").toHaveValue(["foo", "bar"]);
    ```

## Helpers

### DOM
- getFixture

- getFocusableElements

- getNextFocusableElement

- getPreviousFocusableElement

- getRect

- isDisplayed

- isEditable

- isEventTarget

- isFocusable

- isInDOM

- isVisible

- observe

- queryAll

- queryAllContents

- queryContent

- queryOne

- waitFor

- waitUntil

- watchChildren

- watchKeys


### Events

- check

- clear

- click

- dblclick

- dispatch

- drag

- edit

- fill

- hover

- keyDown

- keyUp

- leave

- on

- pointerDown

- pointerUp

- press

- scroll

- select

- uncheck

- watchListeners


### Mocks

- makeSeededRandom

- mockRandom

- mockFetch

- mockWebSocket

- mockWorker

- flushNotifications

- Deferred

- advanceTime

- animationFrame

- cancelAllTimers

- delay

- microTick

- mockDate

- mockTimeZone

- runAllTimers

- setFrameRate

- tick

- isDocument

- isElement

- isWindow
