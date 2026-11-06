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

# Import the patch a patch relies on

A patch that relies on another patch of the same object (it calls `super` on a method
the other patch adds or changes, or reads what it sets) imports the file of that patch,
even with nothing to import from it.

```js
import { Book } from "@library/core/book_model";

import { patch } from "@web/core/utils/patch";

import "@library/core/web/book_model_patch";

patch(Book.prototype, {
    open() {
        super.open(); // the version of book_model_patch.js
    },
});
```

## Why

Patches apply in the order their files run. Files run in the order of the bundle, except
that a file waits for the files it imports: an import added to either file, or a new
file, can run the two patches the other way round. Without the import, the patch works
by luck and breaks later with no change of its own.

## Exceptions

- Two patches of the same object that change different methods, and read nothing of
  each other, need no import.
