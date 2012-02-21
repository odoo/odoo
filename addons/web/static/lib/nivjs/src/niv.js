/*
Copyright (c) 2011, OpenERP S.A.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met: 

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer. 
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution. 

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

niv = (function() {
	var niv = {};

	/*
     * Simple JavaScript Inheritance By John Resig http://ejohn.org/ MIT
     * Licensed.
     */
	// Inspired by base2 and Prototype
	(function(){
	  var initializing = false, fnTest = /xyz/.test(function(){xyz;}) ? /\b_super\b/ : /.*/;
	  // The base Class implementation (does nothing)
	  this.Class = function(){};
	  
	  // Create a new Class that inherits from this class
	  this.Class.extend = function(prop) {
	    var _super = this.prototype;
	    
	    // Instantiate a base class (but only create the instance,
	    // don't run the init constructor)
	    initializing = true;
	    var prototype = new this();
	    initializing = false;
	    
	    // Copy the properties over onto the new prototype
	    for (var name in prop) {
	      // Check if we're overwriting an existing function
	      prototype[name] = typeof prop[name] == "function" && 
	        typeof _super[name] == "function" && fnTest.test(prop[name]) ?
	        (function(name, fn){
	          return function() {
	            var tmp = this._super;
	            
	            // Add a new ._super() method that is the same method
	            // but on the super-class
	            this._super = _super[name];
	            
	            // The method only need to be bound temporarily, so we
	            // remove it when we're done executing
	            var ret = fn.apply(this, arguments);        
	            this._super = tmp;
	            
	            return ret;
	          };
	        })(name, prop[name]) :
	        prop[name];
	    }
	    
	    // The dummy class constructor
	    function Class() {
	      // All construction is actually done in the init method
	      if ( !initializing && this.init )
	        this.init.apply(this, arguments);
	    }
	    
	    // Populate our constructed prototype object
	    Class.prototype = prototype;
	    
	    // Enforce the constructor to be what we expect
	    Class.prototype.constructor = Class;

	    // And make this class extendable
	    Class.extend = arguments.callee;
	    
	    return Class;
	  };
	}).call(niv);
	
	niv.ParentedMixin = {
	    __parented_mixin: true,
	    setParent: function(parent) {
	        if(this.getParent()) {
	            if (this.getParent().__parented_mixin) {
	                this.getParent().__parented_children = _.without(this.getParent().getChildren(), this);
	            }
	            this.__parented_parent = undefined;
	        }
	        this.__parented_parent = parent;
	        if(parent && parent.__parented_mixin) {
	            if (!parent.getChildren())
	                parent.__parented_children = [];
	            parent.getChildren().push(this);
	        }
	    },
	    getParent: function() {
	        return this.__parented_parent;
	    },
	    getChildren: function() {
	        return this.__parented_children ? _.clone(this.__parented_children) : [];
	    },
	    isDestroyed: function() {
	        return this.__parented_stopped;
	    },
	    destroy: function() {
	        _.each(this.getChildren(), function(el) {
	            el.destroy();
	        });
	        this.setParent(undefined);
	        this.__parented_stopped = true;
	    },
	};

	return niv;
})();
