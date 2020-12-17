odoo.define('@tests/comments', function (require) {
  'use strict';


  let __exports = {};


  /**
   * This is a comment
   */

  const Test = __exports.Test = class Test {
    // This is a comment in a class
  };

  /* cool comment */
  const a = 5; /* another cool comment */

  const b = 5; // hello

  // another one

  const x = "this is a // nice string and should be kept";
  const y = "this is a /* nice string and should be kept */";
  const z = "this is a /* nice string and should be kept";

  /*
    comments
   */
  const aaa = "keep!";
  /*
    comments
   */


  return __exports;

});

