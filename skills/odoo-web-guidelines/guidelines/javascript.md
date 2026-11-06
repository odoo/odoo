# Organize files by feature, not by type

Code is organized by feature, not by type. Instead of folders like `components/`,
`plugins/`, `services/` or `hooks/`, each feature gets one folder holding all of its
files: `notification/` contains the notification component, its plugin, its template
and its styles.

# Avoid getters

A getter hides the fact that a computation happens, and only saves a pair of
parentheses. Write a plain function instead: the call site then shows that code runs,
and it can take an argument the day the computation needs one.

When the value is derived state, an Owl `computed` is the better answer: unlike a
getter, it recomputes only when what it reads changes.

# Avoid patching JavaScript code

Patching (the `patch` function) is strongly discouraged inside Odoo itself. It is fine
outside of Odoo. A patch makes the code hard to reason about, since reading a snippet
no longer tells you what will run, and harder to maintain, since the patch and the code
it targets drift apart. Usually there is a better solution: design a proper extension
point.

# Use `window` members directly, not the `browser` object

Write `setTimeout`, `clearTimeout`, `localStorage`, `navigator` or `addEventListener`
without the `browser.` prefix. The one exception is `window.location`: import
`location` from `@web/core/browser/browser`, since tests cannot patch it on `window`.

The `browser` object was an indirection so that tests could patch timers and other
`window` members. Hoot mocks them on `window` itself, so `browser` is now `window` and
is deprecated. A lot of code still uses it: do not copy it from the code around, and
leave the existing uses alone unless the change touches those lines.
