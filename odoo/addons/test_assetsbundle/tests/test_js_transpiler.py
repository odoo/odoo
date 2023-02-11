# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import transpile_javascript


@tagged('post_install', '-at_install')
class TestJsTranspiler(TransactionCase):
    maxDiff = None

    def test_01_alias(self):
        input_content = """/** @odoo-module alias=test_assetsbundle.Alias **/"""
        result = transpile_javascript("/test_assetsbundle/static/src/alias.js", input_content)

        expected_result = """odoo.define('@test_assetsbundle/alias', async function (require) {
'use strict';
let __exports = {};
/** @odoo-module alias=test_assetsbundle.Alias **/
return __exports;
});

odoo.define(`test_assetsbundle.Alias`, async function(require) {
                        return require('@test_assetsbundle/alias')[Symbol.for("default")];
                        });
"""

        self.assertEqual(result, expected_result)

    def test_02_default(self):
        input_content = """/** @odoo-module alias=test_assetsbundle.Alias default=False **/"""
        result = transpile_javascript("/test_assetsbundle/static/src/alias.js", input_content)

        expected_result = """odoo.define('@test_assetsbundle/alias', async function (require) {
'use strict';
let __exports = {};
/** @odoo-module alias=test_assetsbundle.Alias default=False **/
return __exports;
});

odoo.define(`test_assetsbundle.Alias`, async function(require) {
                        return require('@test_assetsbundle/alias');
                        });
"""

        self.assertEqual(result, expected_result)

        input_content = """/** @odoo-module alias=test_assetsbundle.Alias default=0 **/"""
        result = transpile_javascript("/test_assetsbundle/static/src/alias.js", input_content)

        expected_result = """odoo.define('@test_assetsbundle/alias', async function (require) {
'use strict';
let __exports = {};
/** @odoo-module alias=test_assetsbundle.Alias default=0 **/
return __exports;
});

odoo.define(`test_assetsbundle.Alias`, async function(require) {
                        return require('@test_assetsbundle/alias');
                        });
"""

        self.assertEqual(result, expected_result)

        input_content = """/** @odoo-module alias=test_assetsbundle.Alias default=false **/"""
        result = transpile_javascript("/test_assetsbundle/static/src/alias.js", input_content)

        expected_result = """odoo.define('@test_assetsbundle/alias', async function (require) {
'use strict';
let __exports = {};
/** @odoo-module alias=test_assetsbundle.Alias default=false **/
return __exports;
});

odoo.define(`test_assetsbundle.Alias`, async function(require) {
                        return require('@test_assetsbundle/alias');
                        });
"""

        self.assertEqual(result, expected_result)

    def test_03_classes(self):
        input_content = """export default class Nice {}

class Vehicule {}

export class Car extends Vehicule {}

export class Boat extends Vehicule {}

export const Ferrari = class Ferrari extends Car {};
"""
        result = transpile_javascript("/test_assetsbundle/static/src/classes.js", input_content)

        expected_result = """odoo.define('@test_assetsbundle/classes', async function (require) {
'use strict';
let __exports = {};
const Nice = __exports[Symbol.for("default")] = class Nice {}

class Vehicule {}

const Car = __exports.Car = class Car extends Vehicule {}

const Boat = __exports.Boat = class Boat extends Vehicule {}

const Ferrari = __exports.Ferrari = class Ferrari extends Car {};

return __exports;
});
"""

        self.assertEqual(result, expected_result)

    def test_04_comments(self):
        input_content = """/**
 * This is a comment
 */

/**
 * This isn't a string
 */
export class Test {
  // This is a comment in a class
}

/* cool comment */ const a = 5; /* another cool comment */

const b = 5; // hello

// another one

const y = "this is a /* nice string and should be kept */";
const z = "this is a /* nice string and should be kept";
export const x = "this is a // nice string and should be kept";
const w = "this is a */ nice string and should be kept";

// This isn't a string
/*
  comments
 */
const aaa = "keep!";
/*
  comments
 */
"""
        result = transpile_javascript("/test_assetsbundle/static/src/comments.js", input_content)

        expected_result = """odoo.define('@test_assetsbundle/comments', async function (require) {
'use strict';
let __exports = {};
/**
 * This is a comment
 */

/**
 * This isn't a string
 */
const Test = __exports.Test = class Test {
  // This is a comment in a class
}

/* cool comment */ const a = 5; /* another cool comment */

const b = 5; // hello

// another one

const y = "this is a /* nice string and should be kept */";
const z = "this is a /* nice string and should be kept";
const x = __exports.x = "this is a // nice string and should be kept";
const w = "this is a */ nice string and should be kept";

// This isn't a string
/*
  comments
 */
const aaa = "keep!";
/*
  comments
 */

return __exports;
});
"""

        self.assertEqual(result, expected_result)

    def test_05_functions(self):
        input_content = """export function sayHello() {
  console.log("Hello");
}

export function sayHelloWorld() {
  console.log("Hello world");
}

export async function sayAsyncHello() {
  console.log("Hello Async");
}


export default function sayHelloDefault() {
  console.log("Hello Default");
}
"""
        result = transpile_javascript("/test_assetsbundle/static/src/functions.js", input_content)

        expected_result = """odoo.define('@test_assetsbundle/functions', async function (require) {
'use strict';
let __exports = {};
__exports.sayHello = sayHello; function sayHello() {
  console.log("Hello");
}

__exports.sayHelloWorld = sayHelloWorld; function sayHelloWorld() {
  console.log("Hello world");
}

__exports.sayAsyncHello = sayAsyncHello; async function sayAsyncHello() {
  console.log("Hello Async");
}


__exports[Symbol.for("default")] = sayHelloDefault; function sayHelloDefault() {
  console.log("Hello Default");
}

return __exports;
});
"""

        self.assertEqual(result, expected_result)

    def test_06_import(self):
        input_content = """/**
 * import { Dialog, Notification } from "../src/Dialog";
 */
import { Line1 } from "../src/Dialog";
import { Line2, Notification } from "../src/Dialog";
import { Line3, Notification } from "Dialog";
import { Line4, Notification } from "@tests/Dialog";
import { Line5, Notification } from "./Dialog";
import { Line6, Notification } from '../src/Dialog'
import Line7  from "../src/Dialog";
import  Line8  from '../src/Dialog';

import Line9  from "test.Dialog";
import  { Line10, Notification }  from 'test.Dialog2';

import * as Line11 from "test.Dialog";
import "test.Dialog";

import Line12  from "@test.Dialog"; //HELLO
import {Line13}  from "@test.Dialog" //HELLO


const test = `import { Line14, Notification } from "../src/Dialog";`

import Line15 from "test/Dialog";
import Line16 from "test.Dialog.error";
"""
        result = transpile_javascript("/test_assetsbundle/static/src/import.js", input_content)

        expected_result = """odoo.define('@test_assetsbundle/import', async function (require) {
'use strict';
let __exports = {};
/**
 * import { Dialog, Notification } from "../src/Dialog";
 */
const { Line1 } = require("@test_assetsbundle/Dialog");
const { Line2, Notification } = require("@test_assetsbundle/Dialog");
const { Line3, Notification } = require("Dialog");
const { Line4, Notification } = require("@tests/Dialog");
const { Line5, Notification } = require("@test_assetsbundle/Dialog");
const { Line6, Notification } = require("@test_assetsbundle/Dialog")
const Line7 = require("@test_assetsbundle/Dialog")[Symbol.for("default")];
const Line8 = require("@test_assetsbundle/Dialog")[Symbol.for("default")];

const Line9 = require("test.Dialog");
const { Line10, Notification } = require('test.Dialog2');

const Line11 = require("test.Dialog");
require("test.Dialog");

const Line12 = require("@test.Dialog")[Symbol.for("default")]; //HELLO
const {Line13} = require("@test.Dialog") //HELLO


const test = `import { Line14, Notification } from "../src/Dialog";`

const Line15 = require("test/Dialog");
const Line16 = require("test.Dialog.error");

return __exports;
});
"""

        self.assertEqual(result, expected_result)

    def test_07_index(self):
        input_content = """export const a = 5;

import * as b from "@tests/dir";

import c from "@tests/dir/index/";

import d from "@tests";"""
        result = transpile_javascript("/test_assetsbundle/static/src/index.js", input_content)

        expected_result = """odoo.define('@test_assetsbundle', async function (require) {
'use strict';
let __exports = {};
const a = __exports.a = 5;

const b = require("@tests/dir");

const c = require("@tests/dir")[Symbol.for("default")];

const d = require("@tests")[Symbol.for("default")];
return __exports;
});
"""

        self.assertEqual(result, expected_result)

    def test_08_list(self):
        input_content = """export {a, b};

export {a as aa, b, c as cc};
export {a, aReallyVeryLongNameWithSomeExtra}
export {
        a,
        aReallyVeryLongNameWithSomeExtra,
        }
export {
        a,
        aReallyVeryLongNameWithSomeExtra
        }


export {a, aReallyVeryLongNameWithSomeExtra /* a comment must not cause catastrophic backtracking, even if not supported */};

export {c, d} from "@tests/Dialog";
export {e} from "../src/Dialog";

export {c as cc, d, e as ee} from "@tests/Dialog";

export * from "@tests/Dialog";
"""
        result = transpile_javascript("/test_assetsbundle/static/src/list.js", input_content)

        expected_result = """odoo.define('@test_assetsbundle/list', async function (require) {
'use strict';
let __exports = {};
Object.assign(__exports, {a,  b});

Object.assign(__exports, {aa: a,  b, cc:  c});
Object.assign(__exports, {a,  aReallyVeryLongNameWithSomeExtra})
Object.assign(__exports, {
        a, 
        aReallyVeryLongNameWithSomeExtra, 
        })
Object.assign(__exports, {
        a, 
        aReallyVeryLongNameWithSomeExtra
        })


export {a, aReallyVeryLongNameWithSomeExtra /* a comment must not cause catastrophic backtracking, even if not supported */};

{const {c, d} = require("@tests/Dialog");Object.assign(__exports, {c,  d})};
{const {e} = require("@test_assetsbundle/Dialog");Object.assign(__exports, {e})};

{const {c, d, e} = require("@tests/Dialog");Object.assign(__exports, {cc: c,  d, ee:  e})};

Object.assign(__exports, require("@tests/Dialog"));

return __exports;
});
"""

        self.assertEqual(result, expected_result)


    def test_09_variables(self):
        input_content = """export const v = 5;

const a = 12;
const b = 15;

export { a, b };

export default 100;

export default a;
"""
        result = transpile_javascript("/test_assetsbundle/static/src/variables.js", input_content)

        expected_result = """odoo.define('@test_assetsbundle/variables', async function (require) {
'use strict';
let __exports = {};
const v = __exports.v = 5;

const a = 12;
const b = 15;

Object.assign(__exports, { a,  b });

__exports[Symbol.for("default")] = 100;

__exports[Symbol.for("default")] = a;

return __exports;
});
"""

        self.assertEqual(result, expected_result)
