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
- A test that only waits for the final state, with `waitFor` or `contains` and the final
  count, needs no frozen time, as long as no earlier state matches that wait.
