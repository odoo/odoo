odoo.define('energy.controller', function (require) {

    var FormController = require('web.FormController');
    FormController.include({

        test: function() {
          console.log("TEST");
        }
      
      });
      
      console.log(FormController.prototype.test);


});
