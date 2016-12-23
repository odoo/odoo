/*! jQuery Validation Plugin - v1.14.0 - 6/30/2015
 * http://jqueryvalidation.org/
 * Copyright (c) 2015 Jörn Zaefferer; Licensed MIT */
!function(a){"function"==typeof define&&define.amd?define(["jquery","../jquery.validate.min"],a):a(jQuery)}(function(a){a.extend(a.validator.methods,{date:function(a,b){return this.optional(b)||/^\d\d?\.\d\d?\.\d\d\d?\d?$/.test(a)},number:function(a,b){return this.optional(b)||/^-?(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d+)?$/.test(a)}})});