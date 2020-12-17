odoo.define('@tests/classes', function (require) {
  'use strict';

  let __exports = {};

  const Nice = __exports.__default = class Nice {}

  class Vehicule {}

  const Car = __exports.Car = class Car extends Vehicule {};

  const Boat = __exports.Boat = class Boat extends Vehicule {};

  const Ferrari = __exports.Ferrari = class Ferrari extends Car {};

  return __exports;
});


