# Odoo editor

A fast wysiwyg editor targeting documents and website structures.

## Key features
### Unbreakable nodes
When editing some sections of a website,
there is a possibility for a selection to start or end within a node that is
contained in an unbreakable.

If the user deletes the content of the selection, the unbreakable node should not
be merged with another one.

## Demo
To open the demo page:
`http://<host:port>/web_editor/static/lib/odoo-editor/demo/index.html`

## Tests
To open the test page, go to
`http://<host:port>/web_editor/static/lib/odoo-editor/test/editor-test.html`

## Prettify
```bash
# install prettier
npm install -g prettier
# prettify
prettier --config '<odoo-path>/addons/web_editor/static/lib/odoo-editor/_prettierrc.js' --ignore-path='<odoo-path>/odoo/addons/web_editor/static/lib/odoo-editor/_prettierignore' '<odoo-path>/odoo/addons/web_editor/static/lib/odoo-editor/**/*.js'  --write
```

## Prettify with vscode
Install vscode extention `esbenp.prettier-vscode`.

Add the following configuration in your vscode user config or workspace config:
```
"prettier.requireConfig": true,
"prettier.configPath": "<odoo-path>/odoo/addons/web_editor/static/lib/odoo-editor/.prettierrc.js",
"[javascript]": {
  "editor.defaultFormatter": "esbenp.prettier-vscode"
}
```

Then you can use the command `Format Document` or use `ctrl+h` to format a file.

## Guide

### History

Here are the main methods that control how mutations are recorded inside the
editor history:

- `observerUnactive` / `observerActive` will prevent any mutation from being
  recorded.

  Used for:
  - adding elements in the editable that should not be impacted by undo/redo
    or should not be transferred to other peers (in collaboration mode).
  - adding attributes that should not be recorded.
  - visually preview changes in the editable (although, some preview should use
    `historyPauseSteps` / `historyUnpauseSteps` because of the limitation
    described below in the "warning" section).

  Warning:
  - If the insertion of a step is never recorded, all mutation inside that node
    will be skipped. It means that if we use that strategy to "preview" changes
    but the "preview" add/remove some nodes, any further changes within an added
    node that has never been recorder will be discarded.
  - The steps will never be sent to other peers in collaboration mode (it could
    be desirable or not depending on the case).
  - That step can never be undone/redone.

- `historyPauseSteps` / `historyUnpauseSteps` will prevent any `historyStep()`
  from creating a step.

  Used for:
  - `editor.execCommand` automatically call `historyStep`. If we want to perform
    multiples `editor.execCommand` and to only have one step that is discarded
    with `historyRevertCurrentStep()`, or validated with `historyStep()` or
    `historyStep(true)`.
  - If a command like `execCommand` call `historyStep()`, the argument of
    `historyStep` `skipRollback` will be `false`. If we wish to set
    `skipRollback` to true, we can use
    `historyPauseSteps()`/`historyUnpauseSteps()` then `historyStep(true)`.

- `historyRevertCurrentStep` undo all the changes of the `currentStep` (the step
  that has not yet been validated).
  Used for:
  - Visually preview changes in the editable then "cleaning" those changes. This
    avoid adding unnecessary mutations in the history (ie. performance).

- `automaticStepSkipStack` will prevent an automatic step `editor.historyStep()`
  with the argument `skipRollback=false` being created after a timeout.

  Used for:
  - make changes outside an `execCommand` (custom dom changes) that should not
    create a step automatically.

- `filterMutationRecords` is meant to be used only for mutation we know should
  never be recorded.