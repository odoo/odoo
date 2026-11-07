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

# Use the Owl 3 hooks, not the Owl 2 compatibility ones

New code does not call `useLayoutEffect`, `useSubEnv`, `useEnv`, `onWillRender` or
`render()`. They come from the layer that lets Owl 2 code run on Owl 3, and are removed
as each module is migrated. Write instead:

- `useEffect(fn)` for a side effect: it takes no dependency list, and runs again when
  anything it reads changes, including what the functions it calls read.
- `useOnChange(() => [deps], callback)` when only some values must run it again: only the
  dependency function is tracked, not the callback.
- `onMounted` and `onPatched` for work on the DOM after each render, such as a measure.
- `computed` for a value derived from other state.
- `providePlugins` and `usePlugin` to share something with child components.
- a `signal` or a `proxy` read by the template, rather than forcing a render.

The Owl 2 APIs that Owl 3 removed (`useState`, `useRef`, static `props`) fail at once.
These ones keep working, so they get through unnoticed.

Owl 3 `useEffect` is not the Owl 2 one, and a hook converted as is breaks:

- It runs once during setup, before the component is in the DOM, then each time a
  signal, proxy or computed it read changes. Something read inside `untrack`, or that is
  not reactive, never runs it again. A render with no reactive change does not run it.
- A second argument is ignored. An element is read through its `signal.ref()`: `null` at
  the first run, and the effect runs again once the element is set.
- An effect may write state, e.g. reset a selection when the record changes.

```js
// bad: dependencies given by hand, run at mount
useLayoutEffect(
    (isEditing) => isEditing && this.checkAccess(),
    () => [this.record.isEditing],
);

// good: runs at setup, then only when `isEditing` changes, whatever `checkAccess` reads
useOnChange(
    () => [this.record.isEditing],
    (isEditing) => isEditing && this.checkAccess(),
);
```

Code that still calls these hooks keeps them until its own migration: a change that only
touches nearby lines does not have to convert them.
