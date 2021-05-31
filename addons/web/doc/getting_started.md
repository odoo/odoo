# Getting Started

The addon `wowl` is a self-contained web project: it has a `package.json` file
(which makes it a proper `npm` application), a `tsconfig.json` (to configure
typescript), a `rollup.config.js` (to configure the Rollup bundler).

It has typescript supports, xml templates detection, can run tests written in
typescript, it features a livereload server, and more.

## Initial setup

The first and essential task is to install the dependencies defined in the project:
to do that, one need to do the following:

-   have `npm` installed (the `node` package manager, which comes with `node`),
-   open a terminal and move to the `addons/wowl` folder (because it is the root
    of the web project
-   type `npm install`

Once this is done, the commands `npm run build` and `npm run dev` are available
(see next section for more detail).

WARNING: the first and most common error is to run commands in the root of the
odoo project. This will not work! The configuration files are located in the
`addons/wowl` folder, and each command should be run inside that path!

### Configure your IDE

The addon `wowl` is written in typescript. If you're using Sublime Text, install
the TypeScript package from https://www.typescriptlang.org/ to enable type
checking.

WARNING: other TypeScript packages may conflict with this one, so if it isn't
working well, make sure no other is installed.

## Main scripts

-   `npm run build`: build all the assets, which includes the following steps:

    -   compile the typescript `src` files into javascript (output: `static/dist/js/src`)
    -   bundle the js files in a single iife bundle (output: `static/dist/app.js`)
    -   compile the typescript `tests` files into javascript (output: `static/dist/js/tests`)
    -   bundle the test files into a single iife bundle (output: `static/dist/app_tests.ts`)

-   `npm run dev`: main command for developing on this project.

    -   build all the assets
    -   watch the filesystem and rebuild assets if necessary
    -   start a livereload server (port 8070, hardcoded) to make sure that each
        connected browser is refreshed whenever necessary

-   `npm run prettier`: autoformat all the typescript, scss and markdown files
    located in `static/src`, `static/tests` and `doc`.

## Templates

Wowl introduces the support for a new key `owl_qweb` in the odoo manifest
(`__manifest__.py`). This works like `qweb` (but we could not use it because we
want the current `web/` addon to keep working), except that it also support
folders. So, if a folder such as `static/src/components` is added to that
configuration, then each xml files inside (and inside each sub folders) will be
considered a static template, that will be sent to the web client through the
`/wowl/templates/...` route.

In short, if Wowl cannot find a template, it is likely because the `owl_qweb`
key is not set, or incorrect.

## Javascript bundles

For javascript code, Wowl has its specific setup (typescript files are converted
to javascript, then bundled). The bundler (rollup) will start with the `main.ts`
files (in `src/` and in `tests/`) and use that as a starting point, then bundle
all their dependencies.

So, they are detected automatically, but a file needs to be imported somewhere to
be present in the final `app.js` or `app_test.js`.

## Styles

Styles are handled in an unusual way for Odoo: there is a new `style` key in
the manifest, that works like the `owl_qweb` key for templates. This key describes
a list of files or folders. Then, each `scss` file that can be found is added
in a dynamic asset bundle.

The main benefit is that we don't have to manually add all these scss files each
time a new component is created.

## Tests

Unit tests can be written in typescript, using the QUnit framework. As mentioned
above, they should be imported in the `main.ts` file to be included in the
test suite.

To run the test suite, one needs to open the `/wowl/tests` route in a browser.

## Livereload

The WOWL addon provides a livereload feature: once activated, a browser tab will
refresh itself automatically whenever some static assets was modified.

The `npm` script `npm run livereload` (also executed by `npm run dev` will start
a node application that listen on a specific port. The client code will open a
websocket and attempt to connect to the livereload server. If it manages to do
this, you will see the message `[livereload] connection established` in your
browser console.

Note that it works also for the unit [tests](#tests).

## Common issues

### My new code is not executed

This commonly happens when one add a new typescript file into the source code.
This file is properly compiled in JS, but then is not included in the main
bundle `app.js`.

The reason is that the way files are bundled is by starting at `main.js`, then
following all its dependencies (and dependencies of dependencies, ...) to
include them. If your new file is not imported anywhere, it will not be included
in the final bundle.

### System limit for file watchers

It may happen that you encounter an error while running some commands such as
`npm run dev`, related to file watchers:

```
    ENOSPC: System limit for number of file watchers reached...
```

This is probably caused by the livereload features, that need to watch the
file system. Also, note that odoo started in `dev=all` mode also has its own
watchers.

The only solution in that case is to increase the os limit. See
https://howchoo.com/node/node-increase-file-watcher-system-limit for more info.

### File in browser does not match TS code

A common situation arises when one writes some typescript code, then notices that
the javascript code executed on the browser is not the same. There are two
probable causes for this issue:

1. the typescript code was not built because we forgot to run the command
   `npm run build`, or because we don't have a `npm run dev` command running.
   In that case, the solution is simple: just run one of these commands.

2. there is an error in the typescript code, in which case the typescript
   compiler simply does not output a JS file, and the previous file simply remains.
   Obviously, the solution is then to fix the typescript error.
