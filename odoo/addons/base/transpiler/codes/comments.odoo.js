odoo.define('@tests/comments', function (require) {
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
  };

  /* cool comment */
  const a = 5; /* another cool comment */

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

