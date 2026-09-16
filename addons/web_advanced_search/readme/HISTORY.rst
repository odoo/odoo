11.0.1.0.2 (2018-10-31)
~~~~~~~~~~~~~~~~~~~~~~~

* Fix initialization of 1st domain node

  Sometime the dialog is not ready yet, like on EE version.
  Hence when you inject the 1st domain node
  the dialog must be already opened.

  [simahawk]


11.0.1.0.1 (2018-09-18)
~~~~~~~~~~~~~~~~~~~~~~~

* Fix `undefined` in x2m fields

  Before this patch, when searching with the "equals to" operator in any
  x2many field, the searched parameter was always `undefined`.

  The problem was that the underlying field manager implementation was
  treating those fields as x2many, while the widget used was the `one2many`
  one.

  This patch simply mocks the underlying fake record to make think that
  any relational field is always a `one2many`. This sets all pieces in
  place and makes the field manager work as expected, and thus you can
  search as expected too.

* Make linter happy

  [Yajo]


11.0.1.0.0 (2018-07-20)
~~~~~~~~~~~~~~~~~~~~~~~

* Rename, refactor, migrate to v11

  [Yajo]
