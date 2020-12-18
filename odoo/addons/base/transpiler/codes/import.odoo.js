odoo.define('@tests/import', function (require) {
  'use strict';

  let __exports = {};
  /**
   * import { Dialog, Notification } from "../js/Dialog";
   */
  const { Line1} = require("@tests/Dialog");
  const { Line2, Notification} = require("@tests/Dialog");
  const { Line3, Notification} = require("@tests/Dialog");
  const { Line4, Notification} = require("@tests/Dialog");
  const { Line5, Notification} = require("@tests/Dialog");
  const { Line6, Notification} = require("@tests/Dialog");
  const Line7 = require("@tests/Dialog").__default;
  const Line8 = require("@tests/Dialog").__default;

  const Line9 = require("test.Dialog");
  const { Line10, Notification } = require('test.Dialog2');

  const test = `import { Line9, Notification } from "../js/Dialog";`

  return __exports;
});
