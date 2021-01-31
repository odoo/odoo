odoo.define('frepple', function (require) {
  'use strict';

  var core = require('web.core');
  var AbstractAction = require('web.AbstractAction');

  /* Forecast editor page. */
  var ForecastEditor = AbstractAction.extend({
    start: function() {
      this._super.apply(this, arguments);

      var el = this.$el;
      el.height("calc(100% - 34px)");
      this._rpc({
        model: 'res.company',
        method: 'getFreppleURL',
        args: [false, '/forecast/editor/'],
        })
        .then(function(result) {
          el.append('<iframe src="' + result
            + '" width="100%" height="100%" marginwidth="0" marginheight="0" frameborder="no" '
            + ' scrolling="yes" style="border-width:0px;"/>');
          });
    },
    getTitle: function () {
        return "Forecast Editor";
    }
  });
  core.action_registry.add('frepple.forecasteditor', ForecastEditor);

  /* Inventory planning page. */
  var InventoryPlanning = AbstractAction.extend({
    start: function() {
      this._super.apply(this, arguments);

      var el = this.$el;
      el.height("calc(100% - 34px)");
      this._rpc({
        model: 'res.company',
        method: 'getFreppleURL',
        args: [false, '/inventoryplanning/drp/'],
        })
        .then(function(result) {
          el.append('<iframe src="' + result
            + '" width="100%" height="100%" marginwidth="0" marginheight="0" frameborder="no" '
            + ' scrolling="yes" style="border-width:0px;"/>');
          });
    },
    getTitle: function () {
        return "Inventory Planning";
    }
  });
  core.action_registry.add('frepple.inventoryplanning', InventoryPlanning);

  /* Plan editor page. */
  var PlanEditor = AbstractAction.extend({
    start: function() {
      this._super.apply(this, arguments);

      var el = this.$el;
      el.height("calc(100% - 34px)");
      this._rpc({
        model: 'res.company',
        method: 'getFreppleURL',
        args: [false, '/planningboard/'],
        })
        .then(function(result) {
          el.append('<iframe src="' + result
            + '" width="100%" height="100%" marginwidth="0" marginheight="0" frameborder="no" '
            + ' scrolling="yes" style="border-width:0px;"/>');
          });
    },
    getTitle: function () {
        return "Plan Editor";
    }
  });
  core.action_registry.add('frepple.planeditor', PlanEditor);

  /* Full user interface page. */
  var HomePage = AbstractAction.extend({
    start: function() {
      this._super.apply(this, arguments);

      var el = this.$el;
      el.height("calc(100% - 34px)");
      this._rpc({
        model: 'res.company',
        method: 'getFreppleURL',
        args: [true, '/'],
        })
        .then(function(result) {
          el.append('<iframe src="' + result
            + '" width="100%" height="100%" marginwidth="0" marginheight="0" frameborder="no" '
            + ' scrolling="yes" style="border-width:0px;"/>');
          });
    },
    getTitle: function () {
        return "frePPLe";
    }
  });
  core.action_registry.add('frepple.homepage', HomePage);

  return {
    'frepple.forecasteditor': ForecastEditor,
    'frepple.inventoryplanning': InventoryPlanning,
    'frepple.planeditor': PlanEditor,
    'frepple.homepage': HomePage,
  };
});
