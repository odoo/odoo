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
