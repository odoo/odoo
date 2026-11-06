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

# Name a value for what it holds

Name a variable, a function or a prop for what its value really is, and let its JSDoc
say the same: a date formatted as a string is `dateStr`, not `date`; `isPublished` is
true only when the record is published; `hasAttachments` returns true only when there
are attachments. When a change makes a value hold something else, rename it in the
same change.

A name that matches the value lets the reader follow the code without opening what
builds the value. A name that says more or other than the value holds makes the reader
check it each time.

A name that other modules use (a field, a prop, a route parameter) is an API: in a
stable version it stays, and the JSDoc says what the value really holds.

# Avoid patching JavaScript code

Patching (the `patch` function) is strongly discouraged inside Odoo itself. It is fine
outside of Odoo. A patch makes the code hard to reason about, since reading a snippet
no longer tells you what will run, and harder to maintain, since the patch and the code
it targets drift apart. Usually there is a better solution: design a proper extension
point.
