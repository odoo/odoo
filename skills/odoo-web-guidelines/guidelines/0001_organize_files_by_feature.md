# Organize files by feature, not by type

Every file belonging to a feature goes in one directory named after that feature. The
feature directory may sit under a grouping directory such as `core/` or `views/`; what
matters is that one directory, named after the feature, holds all of its files.

```
static/src/
    core/
        notification/
            notification.js
            notification.scss
            notification.xml
            notification_container.js
            notification_plugin.js
```

When a feature ships in several asset bundles, the split happens inside its directory,
one subdirectory per bundle, the shared part in `common/`. Feature first, then bundle:

```
static/src/
    thread/
        common/
            thread.js
            thread.xml
        web/
            thread_patch.js
```

Do not group files by what kind of file they are:

```
static/src/
    components/
        notification.js
        notification_container.js
    plugins/
        notification_plugin.js
    scss/
        notification.scss
    xml/
        notification.xml
```

The two notification trees contain the same files. The first tells you the codebase has
a notification feature. The second tells you the codebase has components.

## Why

- Files that change together live together. Touching a feature usually means touching
  its component, its plugin and its template at the same time.
- You can read a feature by listing one directory. No need to hunt for files.
- Deleting the feature is deleting one directory, and what is left behind is easy to
  spot.

## When it does not apply

Code that belongs to no feature in particular goes in a generic directory such as
`utils/`. Keep it small.
