# Prototype
snippet proto
	${1:class_name}.prototype.${2:method_name} = function(${3:first_argument}) {
		${4:// body...}
	};
# Function
snippet fun
	function ${1?:function_name}(${2:argument}) {
		${3:// body...}
	}
# Anonymous Function
regex /((=)\s*|(:)\s*|(\()|\b)/f/(\))?/
snippet f
	function${M1?: ${1:functionName}}($2) {
		${0:$TM_SELECTED_TEXT}
	}${M2?;}${M3?,}${M4?)}
# Immediate function
trigger \(?f\(
endTrigger \)?
snippet f(
	(function(${1}) {
		${0:${TM_SELECTED_TEXT:/* code */}}
	}(${1}));
# if
snippet if
	if (${1:true}) {
		${0}
	}
# if ... else
snippet ife
	if (${1:true}) {
		${2}
	} else {
		${0}
	}
# tertiary conditional
snippet ter
	${1:/* condition */} ? ${2:a} : ${3:b}
# switch
snippet switch
	switch (${1:expression}) {
		case '${3:case}':
			${4:// code}
			break;
		${5}
		default:
			${2:// code}
	}
# case
snippet case
	case '${1:case}':
		${2:// code}
		break;
	${3}

# while (...) {...}
snippet wh
	while (${1:/* condition */}) {
		${0:/* code */}
	}
# try
snippet try
	try {
		${0:/* code */}
	} catch (e) {}
# do...while
snippet do
	do {
		${2:/* code */}
	} while (${1:/* condition */});
# Object Method
snippet :f
regex /([,{[])|^\s*/:f/
	${1:method_name}: function(${2:attribute}) {
		${0}
	}${3:,}
# setTimeout function
snippet setTimeout
regex /\b/st|timeout|setTimeo?u?t?/
	setTimeout(function() {${3:$TM_SELECTED_TEXT}}, ${1:10});
# Get Elements
snippet gett
	getElementsBy${1:TagName}('${2}')${3}
# Get Element
snippet get
	getElementBy${1:Id}('${2}')${3}
# console.log (Firebug)
snippet cl
	console.log(${1});
# return
snippet ret
	return ${1:result}
# for (property in object ) { ... }
snippet fori
	for (var ${1:prop} in ${2:Things}) {
		${0:$2[$1]}
	}
# hasOwnProperty
snippet has
	hasOwnProperty(${1})
# docstring
snippet /**
	/**
	 * ${1:description}
	 *
	 */
snippet @par
regex /^\s*\*\s*/@(para?m?)?/
	@param {${1:type}} ${2:name} ${3:description}
snippet @ret
	@return {${1:type}} ${2:description}
# JSON.parse
snippet jsonp
	JSON.parse(${1:jstr});
# JSON.stringify
snippet jsons
	JSON.stringify(${1:object});
# self-defining function
snippet sdf
	var ${1:function_name} = function(${2:argument}) {
		${3:// initial code ...}

		$1 = function($2) {
			${4:// main code}
		};
	}
# singleton
snippet sing
	function ${1:Singleton} (${2:argument}) {
		// the cached instance
		var instance;

		// rewrite the constructor
		$1 = function $1($2) {
			return instance;
		};
		
		// carry over the prototype properties
		$1.prototype = this;

		// the instance
		instance = new $1();

		// reset the constructor pointer
		instance.constructor = $1;

		${3:// code ...}

		return instance;
	}
# class
snippet class
regex /^\s*/clas{0,2}/
	var ${1:class} = function(${20}) {
		$40$0
	};
	
	(function() {
		${60:this.prop = ""}
	}).call(${1:class}.prototype);
	
	exports.${1:class} = ${1:class};
# 
snippet for-
	for (var ${1:i} = ${2:Things}.length; ${1:i}--; ) {
		${0:${2:Things}[${1:i}];}
	}
# for (...) {...}
snippet for
	for (var ${1:i} = 0; $1 < ${2:Things}.length; $1++) {
		${3:$2[$1]}$0
	}
# for (...) {...} (Improved Native For-Loop)
snippet forr
	for (var ${1:i} = ${2:Things}.length - 1; $1 >= 0; $1--) {
		${3:$2[$1]}$0
	}


#modules
snippet def
	define(function(require, exports, module) {
	"use strict";
	var ${1/.*\///} = require("${1}");
	
	$TM_SELECTED_TEXT
	});
snippet req
guard ^\s*
	var ${1/.*\///} = require("${1}");
	$0
snippet requ
guard ^\s*
	var ${1/.*\/(.)/\u$1/} = require("${1}").${1/.*\/(.)/\u$1/};
	$0
