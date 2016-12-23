/*! jQuery Validation Plugin - v1.14.0 - 6/30/2015
 * http://jqueryvalidation.org/
 * Copyright (c) 2015 Jörn Zaefferer; Licensed MIT */
!function(a){"function"==typeof define&&define.amd?define(["jquery","../jquery.validate.min"],a):a(jQuery)}(function(a){a.extend(a.validator.methods,{date:function(a,b){return this.optional(b)||/^\d{1,2}\.\d{1,2}\.\d{4}$/.test(a)},number:function(a,b){return this.optional(b)||/^-?(?:\d+)(?:,\d+)?$/.test(a)}})});