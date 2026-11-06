# Pair every absence check with a positive one

In a Hoot test or a tour, a check that an element is absent (`toHaveCount(0)`,
`not.toHaveCount()`, `waitForNone`, `{ count: 0 }`, a trigger built on
`:not(:has(...))`) comes after a positive check in the same test, on an element that
only the state under test produces: the same element before the step that removes it,
or the result of the step after which the element must not show.

An absence is true from the start. Checked before the code under test ran, it passes;
on a misspelled or renamed selector, it passes forever. The positive check proves that
the step happened and, when it is on the same element, that the selector matches real
markup.

When the element must never show, the positive check alone is not enough: the step can
render its result in one animation frame and the forbidden element in the next one.
Wait one more frame (`await animationFrame()`) before the absence check, and run the
test once on the broken code to see it fail: here, that run is the only proof that the
selector matches real markup.

```js
// Bad: passes before the error had a chance to show.
await contains(".o_send").click();
expect(".o_error").toHaveCount(0);

// Good: the message is sent, one more frame is rendered, and still no error.
await contains(".o_send").click();
await waitFor(".o_message");
await animationFrame();
expect(".o_error").toHaveCount(0);
```

# Freeze the time when a test meets a timer

A Hoot test that triggers a debounced or delayed call (a search as you type, an
autosave, a popover that opens after a delay) calls `freezeTime()` before the action,
then fires the timer with `advanceTime`. When the timer fires is decided by
`advanceTime`, never by the real clock.

```js
// bad: green only while the 250 ms debounce has not fired yet
await contains(".o_library_search input").edit("Dune", { confirm: false });
expect.verifySteps([]);

// good: the search runs when the test says so
freezeTime();
await contains(".o_library_search input").edit("Dune", { confirm: false });
expect.verifySteps([]);
await advanceTime(250);
expect.verifySteps(["search_books"]);
```

## Why

Hoot replaces the timers of the code, but they still run on the real clock until the
test calls `freezeTime()`; `mockDate` does not stop them. On a developer machine the
test ends before a 250 ms debounce and passes. On a loaded build the timer fires in the
middle of the test, and the test fails at random.

## Exceptions

- Once the time is frozen, every timer of the code waits for `advanceTime`, a 0 ms one
  too: freeze it after the steps that need one, or advance the time after them.
- A test that only waits for the final state, with `waitFor` and the final count, needs
  no frozen time, as long as no earlier state matches that wait.
