odoo.define('@tests/comments', function (require) {
  let __exports = {};

  const Test = __exports.Test = class Test {

  };

  const a = 5;

  const b = 5;

  const x = "this is a // nice string and should be kept";
  const y = "this is a /* nice string and should be kept */";
  const z = "this is a /* nice string and should be kept";

  const aaa = "keep!";

  return __exports;

});

