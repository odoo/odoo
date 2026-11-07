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

# Order concurrent calls with the concurrency helpers

When a call can start before the previous one has ended (a request on each key or each
click), order the calls with a helper of `@web/core/utils/concurrency`, never with a
promise chain kept by hand:

- `KeepLast` when only the last answer matters, as for a search: `add(promise)` returns
  a promise that never settles when a newer promise is added before `promise` settled.
- `Mutex` when every call must run, one after the other, as for a save: `exec(fn)`
  starts `fn` once the previous call has settled, resolved or rejected.

```js
// bad: after one failed request, no later request is ever sent
this.lastSave = this.lastSave.then(() => this.saveQuantity(quantity));

// good
return this.saveMutex.exec(() => this.saveQuantity(quantity));
```

Without a helper, the answers come back in any order: the screen shows the answer of an
older request, or two calls change the same state at once. A chain kept by hand rewrites
`Mutex`, and a `then` with no rejection handler stops it for good at the first error.

Never await a `KeepLast` promise inside `Mutex.exec`: once a newer call replaces it, it
never settles, and the mutex stays locked.

# JavaScript formatting

- Format: 4-space indent, 100-column lines, double quotes, semicolons, as set by the
  `prettier/prettier` rule of the eslint config of the web tooling (`addons/web/tooling`).
  Apply it with `eslint --fix`, never with `prettier` alone: without those options it
  uses its own defaults (2 spaces, 80 columns) and reflows the whole file.
- A file that the eslint config ignores keeps its own format: only the lines you write
  follow the one above.
