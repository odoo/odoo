# Command Category Registry

## Overview

The `commandCategoryRegistry` gathers the command categories.

## Key Usage

The keys in this registry can be used in two differents ways in order to organize the command palette:

-   when registering a new command: `useCommand({ category: "key", ... })`.

-   applied as an attribute in the document: `[data-command-category="key"]`.
    N.B.: if an element should appear in the command palette
    (e.g. it has a `[data-hotkey]` attribute), the closest parent (including itself)
    having a `[data-command-category]` will provide the category key to seek for in the registry.

## Value Type

`{ label?: string }` where `label` is the displayed name of the category in the command palette. Can be undefined.

## Available Categories

| Key       | Sequence | Description          |
| --------- | -------- | -------------------- |
| `main`    | 10       | Main Commands        |
| `app`     | 20       | Current App Commands |
| `actions` | 30       | More Actions         |
| `navbar`  | 40       | NavBar               |
| `default` | 100      | Other commands       |
