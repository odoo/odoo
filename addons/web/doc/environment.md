# Environment

## Overview

Each Owl application runs in a specific environment, which contains many (mostly)
global informations about the application. Odoo is no different, and adds a few
important data in the environment. Here is a description of its content:

## Content

| Key          | Description                                              |
| ------------ | -------------------------------------------------------- |
| `browser`    | list of [browser](browser.md) entities with side effects |
| `bus`        | main application bus                                     |
| `qweb`       | application current `QWeb` rendering engine              |
| `registries` | object containing all relevant registries                |
| `services`   | values of all deployed [services](services/readme.md)    |
| `_t`         | eager [translation function](localization.md#_t)         |
