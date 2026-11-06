# Organize files by feature, not by type

Code is organized by feature, not by type. Instead of folders like `components/`,
`plugins/`, `services/` or `hooks/`, each feature gets one folder holding all of its
files: `notification/` contains the notification component, its plugin, its template
and its styles.

# End a sort comparator on a unique key

A comparator given to `sort()` or `toSorted()` returns 0 when its two arguments are
equal and the opposite sign when they are swapped. When the values it compares can be
equal, it ends on a unique key of the items, usually `id`.

```js
// bad: the comparator answers -1 both ways for two books with the same
// title, so their order depends on the engine
books.sort((a, b) => (a.title > b.title ? 1 : -1));

// bad: two books with the same title keep the order they came in
books.sort((a, b) => a.title.localeCompare(b.title));

// good
books.sort((a, b) => a.title.localeCompare(b.title) || a.id - b.id);
```

A comparator that is not anti-symmetric gives an order that depends on the engine and
on the input: Chrome and Firefox do not sort the same way. A comparator that returns 0
for two different items keeps them in the order they came in, and that order changes
with another load or a list updated by a notification. In both cases the user sees rows
swap, and a test that reads the first item fails on one browser or at random.

No fallback is needed when the compared key is already unique, nor for `sort()` without
a comparator on strings. Numbers always need a comparator (`(a, b) => a - b`): the
default sort compares them as strings.

# Batch RPCs

No RPC (an `orm` call, `rpc()`) inside a loop, and no second RPC awaited after the
first one for the same user action. Send one call for all the records (`orm.read` and
`orm.write` take a list of ids, `orm.webSave` writes and reads back in one call), or
add a server method that does the whole action and returns what the client needs.

Each RPC is a network round trip and its own transaction. A loop of awaited calls costs
one round trip per item, so the action gets slower as the data grows. Two calls in a row
double the wait, and when the second one fails, the first one is already committed.
It is the client side of
[Batch ORM calls](../../odoo-guidelines/guidelines/performance.md#batch-orm-calls).

Calls that are independent and cannot become one server call run in parallel
(`Promise.all`). A device or an external service that only takes one item at a time is
an exception, and so is a second call that needs the answer of the first (an action to
load, a wizard to confirm) when no server method can do both.

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
