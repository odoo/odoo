/**
 * Curry - Function currying
 * Copyright (c) 2008 Ariel Flesler - aflesler(at)gmail(dot)com | http://flesler.blogspot.com
 * Licensed under BSD (http://www.opensource.org/licenses/bsd-license.php)
 * Date: 10/4/2008
 *
 * @author Ariel Flesler
 * @version 1.0.1
 */

function curry( fn ){
	return function(){
		var args = curry.args(arguments),
			master = arguments.callee,
			self = this;

		return args.length >= fn.length ? fn.apply(self,args) :	function(){
			return master.apply( self, args.concat(curry.args(arguments)) );
		};
	};
};

curry.args = function( args ){
	return Array.prototype.slice.call(args);
};

Function.prototype.curry = function(){
	return curry(this);
};