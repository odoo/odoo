odoo.define('energy.contract', function(require) {

    var FormController = require('web.FormController');
    var ListView = require('web.ListView');
    var core = require('web.core');
    console.log("START EXTEND");

   

    FormController.include({


    init: function() {
            this._super.apply(this, arguments);
            this._onViewLoaded = this._onViewLoaded || this._super._onViewLoaded;
            this._super._onViewLoaded = this._onViewLoaded.bind(this);
        },
  

    _onViewLoaded: function(viewInfo) {
        console.log("onViewLoaded");

        // Check if contract model
        if (viewInfo.model === 'contract') {

        console.log("Loaded contract view");

        // Access view elements
        //var $loadshape = viewInfo.$el.find(...);

        // Add custom logic  
        //$loadshape.doSomething(); 

        }

    }

});
          console.log(FormController.prototype.init);
          console.log(FormController.prototype._onViewLoaded);


  });