/*
 Copyright (c) 2012-2017 Open Lab
 Permission is hereby granted, free of charge, to any person obtaining
 a copy of this software and associated documentation files (the
 "Software"), to deal in the Software without restriction, including
 without limitation the rights to use, copy, modify, merge, publish,
 distribute, sublicense, and/or sell copies of the Software, and to
 permit persons to whom the Software is furnished to do so, subject to
 the following conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
 LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
 WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

var muteAlertOnChange = false;


// isRequired ----------------------------------------------------------------------------

//return true if every mandatory field is filled and highlight empty ones
jQuery.fn.isFullfilled = function () {
	var canSubmit = true;
	var firstErrorElement = "";

	this.each(function () {
		var theElement = $(this);
		theElement.removeClass("formElementsError");
		//if (theElement.val().trim().length == 0 || theElement.attr("invalid") == "true") {  //robicch 13/2/15
		if (theElement.is("[required]") && theElement.val().trim().length == 0 || theElement.attr("invalid") == "true") {
			if (theElement.attr("type") == "hidden") {
				theElement = theElement.prevAll("#" + theElement.prop("id") + "_txt:first");
			} else if (theElement.is("[withTinyMCE]")){
        if (tinymce.activeEditor.getContent()=="")
          theElement=$("#"+theElement.attr("name")+"_tbl");
        else
          return true;// in order to continue the loop
      }
			theElement.addClass("formElementsError");
			canSubmit = false;

			if (firstErrorElement == "")
				firstErrorElement = theElement;
		}
	});

	if (!canSubmit) {
		// get the tabdiv
		var theTabDiv = firstErrorElement.closest(".tabBox");
		if (theTabDiv.length > 0)
			clickTab(theTabDiv.attr("tabId"));

		// highlight element
		firstErrorElement.effect("highlight", { color:"red" }, 1500);
	}
	return canSubmit;

};

function canSubmitForm(formOrId) {
	//console.debug("canSubmitForm",formOrId);
	if (typeof formOrId != "object")
		formOrId=$("#" + formOrId);
	return formOrId.find(":input[required],:input[invalid=true]").isFullfilled();
}

function showSavingMessage() {
	$("#savingMessage:hidden").fadeIn();
	$("body").addClass("waiting");
	$(window).resize();
}
function hideSavingMessage() {
	$("#savingMessage:visible").fadeOut();
	$("body").removeClass("waiting");
	$(window).resize();
}



/* Types Function */

function isValidURL(url) {
	var RegExp = /^(([\w]+:)?\/\/)?(([\d\w]|%[a-fA-f\d]{2,2})+(:([\d\w]|%[a-fA-f\d]{2,2})+)?@)?([\d\w][-\d\w]{0,253}[\d\w]\.)+[\w]{2,4}(:[\d]+)?(\/([-+_~.\d\w]|%[a-fA-f\d]{2,2})*)*(\?(&?([-+_~.\d\w]|%[a-fA-f\d]{2,2})=?)*)?(#([-+_~.\d\w]|%[a-fA-f\d]{2,2})*)?$/;
	return RegExp.test(url);
}

function isValidEmail(email) {
	//var RegExp = /^((([a-z]|[0-9]|!|#|$|%|&|'|\*|\+|\-|\/|=|\?|\^|_|`|\{|\||\}|~)+(\.([a-z]|[0-9]|!|#|$|%|&|'|\*|\+|\-|\/|=|\?|\^|_|`|\{|\||\}|~)+)*)@((((([a-z]|[0-9])([a-z]|[0-9]|\-){0,61}([a-z]|[0-9])\.))*([a-z]|[0-9])([a-z]|[0-9]|\-){0,61}([a-z]|[0-9])\.)[\w]{2,4}|(((([0-9]){1,3}\.){3}([0-9]){1,3}))|(\[((([0-9]){1,3}\.){3}([0-9]){1,3})\])))$/;
	var RegExp = /^.+@\S+\.\S+$/;
	return RegExp.test(email);
}

function isValidInteger(n) {
	reg = new RegExp("^[-+]{0,1}[0-9]*$");
	return reg.test(n) || isNumericExpression(n);
}

function isValidDouble(n) {
	var sep = Number.decimalSeparator;
	reg = new RegExp("^[-+]{0,1}[0-9]*[" + sep + "]{0,1}[0-9]*$");
	return reg.test(n) || isNumericExpression(n);
}

function isValidTime(n) {
	return !isNaN(millisFromHourMinute(n));
}

function isValidDurationDays(n) {
	return !isNaN(daysFromString(n));
}

function isValidDurationMillis(n) {
	return !isNaN(millisFromString(n));
}

function isNumericExpression(expr) {
	try {
		var a = eval(expr);
		return typeof(a) == 'number';
	} catch (t) {
		return false;
	}

}

function getNumericExpression(expr) {
	var ret;
	try {
		var a = eval(expr);
		if (typeof(a) == 'number')
			ret = a;
	} catch (t) {
	}
	return ret;

}

/*
 supports almost all Java currency format e.g.: ###,##0.00EUR   €#,###.00  #,###.00€  -$#,###.00  $-#,###.00
 */
function isValidCurrency(numStr) {
	//first try to convert format in a regex
	var regex = "";
	var format = Number.currencyFormat + "";

	var minusFound = false;
	var numFound = false;
	var currencyString = "";
	var numberRegex = "[0-9\\" + Number.groupingSeparator + "]+[\\" + Number.decimalSeparator + "]?[0-9]*";

	for (var i = 0; i < format.length; i++) {
		var ch = format.charAt(i);

		if (ch == "." || ch == "," || ch == "0") {
			//skip it
			if (currencyString != "") {
				regex = regex + "(?:" + RegExp.quote(currencyString) + ")?";
				currencyString = "";
			}

		} else if (ch == "#") {
			if (currencyString != "") {
				regex = regex + "(?:" + RegExp.quote(currencyString) + ")?";
				currencyString = "";
			}

			if (!numFound) {
				numFound = true;
				regex = regex + numberRegex;
			}

		} else if (ch == "-") {
			if (currencyString != "") {
				regex = regex + "(?:" + RegExp.quote(currencyString) + ")?";
				currencyString = "";
			}
			if (!minusFound) {
				minusFound = true;
				regex = regex + "[-]?";
			}

		} else {
			currencyString = currencyString + ch;
		}
	}
	if (!minusFound)
		regex = "[-]?" + regex;

	if (currencyString != "")
		regex = regex + "(?:" + RegExp.quote(currencyString) + ")?";

	regex = "^" + regex + "$";

	var rg = new RegExp(regex);
	return rg.test(numStr) || isNumericExpression(numStr);
}

function getCurrencyValue(numStr) {
	if (!isValidCurrency(numStr))
		return NaN;

	var ripul = numStr.replaceAll(Number.groupingSeparator, "").replaceAll(Number.decimalSeparator, ".");
	return getNumericExpression(ripul) || parseFloat(ripul.replace(/[^-0123456789.]/, ""));
}


function formatCurrency(numberString) {
	return formatNumber(numberString, Number.currencyFormat);
}


function formatNumber(numberString, format) {
	if (!format)
		format = "##0.00";

	var dec = Number.decimalSeparator;
	var group = Number.groupingSeparator;
	var neg = Number.minusSign;

	var round = true;

	var validFormat = "0#-,.";

	// strip all the invalid characters at the beginning and the end
	// of the format, and we'll stick them back on at the end
	// make a special case for the negative sign "-" though, so
	// we can have formats like -$23.32
	var prefix = "";
	var negativeInFront = false;
	for (var i = 0; i < format.length; i++) {
		if (validFormat.indexOf(format.charAt(i)) == -1) {
			prefix = prefix + format.charAt(i);
		} else {
			if (i == 0 && format.charAt(i) == '-') {
				negativeInFront = true;
			} else {
				break;
			}
		}
	}
	var suffix = "";
	for (var i = format.length - 1; i >= 0; i--) {
		if (validFormat.indexOf(format.charAt(i)) == -1)
			suffix = format.charAt(i) + suffix;
		else
			break;
	}

	format = format.substring(prefix.length);
	format = format.substring(0, format.length - suffix.length);

	// now we need to convert it into a number
	//while (numberString.indexOf(group) > -1)
	//	numberString = numberString.replace(group, '');
	//var number = new Number(numberString.replace(dec, ".").replace(neg, "-"));
	var number = new Number(numberString);


	var forcedToZero = false;
	if (isNaN(number)) {
		number = 0;
		forcedToZero = true;
	}

	// special case for percentages
	if (suffix == "%")
		number = number * 100;

	var returnString = "";
	if (format.indexOf(".") > -1) {
		var decimalPortion = dec;
		var decimalFormat = format.substring(format.lastIndexOf(".") + 1);

		// round or truncate number as needed
		if (round)
			number = new Number(number.toFixed(decimalFormat.length));
		else {
			var numStr = number.toString();
			numStr = numStr.substring(0, numStr.lastIndexOf('.') + decimalFormat.length + 1);
			number = new Number(numStr);
		}

		var decimalValue = number % 1;
		var decimalString = new String(decimalValue.toFixed(decimalFormat.length));
		decimalString = decimalString.substring(decimalString.lastIndexOf(".") + 1);

		for (var i = 0; i < decimalFormat.length; i++) {
			if (decimalFormat.charAt(i) == '#' && decimalString.charAt(i) != '0') {
				decimalPortion += decimalString.charAt(i);
			} else if (decimalFormat.charAt(i) == '#' && decimalString.charAt(i) == '0') {
				var notParsed = decimalString.substring(i);
				if (notParsed.match('[1-9]')) {
					decimalPortion += decimalString.charAt(i);
				} else {
					break;
				}
			} else if (decimalFormat.charAt(i) == "0") {
				decimalPortion += decimalString.charAt(i);
			}
		}
		returnString += decimalPortion;
	} else {
		number = Math.round(number);
	}
	var ones = Math.floor(number);
	if (number < 0)
		ones = Math.ceil(number);

	var onesFormat = "";
	if (format.indexOf(".") == -1)
		onesFormat = format;
	else
		onesFormat = format.substring(0, format.indexOf("."));

	var onePortion = "";
	if (!(ones == 0 && onesFormat.substr(onesFormat.length - 1) == '#') || forcedToZero) {
		// find how many digits are in the group
		var oneText = new String(Math.abs(ones));
		var groupLength = 9999;
		if (onesFormat.lastIndexOf(",") != -1)
			groupLength = onesFormat.length - onesFormat.lastIndexOf(",") - 1;
		var groupCount = 0;
		for (var i = oneText.length - 1; i > -1; i--) {
			onePortion = oneText.charAt(i) + onePortion;
			groupCount++;
			if (groupCount == groupLength && i != 0) {
				onePortion = group + onePortion;
				groupCount = 0;
			}
		}

		// account for any pre-data padding
		if (onesFormat.length > onePortion.length) {
			var padStart = onesFormat.indexOf('0');
			if (padStart != -1) {
				var padLen = onesFormat.length - padStart;

				// pad to left with 0's or group char
				var pos = onesFormat.length - onePortion.length - 1;
				while (onePortion.length < padLen) {
					var padChar = onesFormat.charAt(pos);
					// replace with real group char if needed
					if (padChar == ',')
						padChar = group;
					onePortion = padChar + onePortion;
					pos--;
				}
			}
		}
	}

	if (!onePortion && onesFormat.indexOf('0', onesFormat.length - 1) !== -1)
		onePortion = '0';

	returnString = onePortion + returnString;

	// handle special case where negative is in front of the invalid characters
	if (number < 0 && negativeInFront && prefix.length > 0)
		prefix = neg + prefix;
	else if (number < 0)
		returnString = neg + returnString;

	if (returnString.lastIndexOf(dec) == returnString.length - 1) {
		returnString = returnString.substring(0, returnString.length - 1);
	}
	returnString = prefix + returnString + suffix;
	return returnString;
}


//validation functions - used by textfield and datefield
jQuery.fn.validateField = function () {
	var isValid = true;

	this.each(function () {
		var el = $(this);
		el.clearErrorAlert();

		var value = el.val();
		if (value) {
			var rett = true;
			var type = (el.attr('entryType')+"").toUpperCase();
			var errParam;

			if (type == "INTEGER") {
				rett = isValidInteger(value);
			} else if (type == "DOUBLE") {
				rett = isValidDouble(value);
			} else if (type == "PERCENTILE") {
				rett = isValidDouble(value);
			} else if (type == "URL") {
				rett = isValidURL(value);
			} else if (type == "EMAIL") {
				rett = isValidEmail(value);
			} else if (type == "DURATIONMILLIS") {
				rett = isValidDurationMillis(value);
			} else if (type == "DURATIONDAYS") {
				rett = isValidDurationDays(value);
			} else if (type == "DATE") {
				rett = Date.isValid(value, el.attr("format"), true);
				if (!rett)
					errParam = el.attr("format");
			} else if (type == "TIME") {
				rett = isValidTime(value);
			} else if (type == "CURRENCY") {
				rett = isValidCurrency(value);
			}

			if (!rett) {
				el.createErrorAlert(i18n.ERROR_ON_FIELD, i18n.INVALID_DATA + (errParam ? " " + errParam : ""));
				isValid=false;
			}


			//check limits  minValue : maxValue
			if (rett && (el.attr("minValue") || el.attr("maxValue"))){
				var val=value;
				var min=el.attr("minValue");
				var max=el.attr("maxValue");
				if (type == "INTEGER") {
					val=parseInt(value);
					min=parseInt(min);
					max=parseInt(max);
				} else if (type == "DOUBLE" || type == "PERCENTILE") {
					val=parseDouble(value);
					min=parseDouble(min);
					max=parseDouble(max);
				} else if (type == "URL") {
					val=value;
				} else if (type == "EMAIL") {
					val=value;
				} else if (type == "DURATIONMILLIS") {
					val=millisFromString(value);
					min=millisFromString(min);
					max=millisFromString(max);

				} else if (type == "DURATIONDAYS") {
					val=daysFromString(value);
					min=daysFromString(min);
					max=daysFromString(max);
				} else if (type == "DATE") {
					val=Date.parseString(value, el.attr("format"),true).getTime();
					min=Date.parseString(min, el.attr("format"),true).getTime();
					max=Date.parseString(max, el.attr("format"),true).getTime();
				} else if (type == "TIME") {
					val = millisFromHourMinute(value);
					min = millisFromHourMinute(min);
					max = millisFromHourMinute(max);
				} else if (type == "CURRENCY") {
					val=getCurrencyValue(value);
					min=getCurrencyValue(min);
					max=getCurrencyValue(max);
				}

				if (el.attr("minValue") && val<min){
					el.createErrorAlert(i18n.ERROR_ON_FIELD, i18n.OUT_OF_BOUDARIES + " ("+el.attr("minValue")+" : "+(el.attr("maxValue")?el.attr("maxValue"):"--")+")");
					rett=false;
					isValid=false;

					$("body").trigger("error");
				}

				if (rett && el.attr("maxValue") && val>max){
					el.createErrorAlert(i18n.ERROR_ON_FIELD, i18n.OUT_OF_BOUDARIES + " ("+(el.attr("minValue")?el.attr("minValue"):"--")+" : "+el.attr("maxValue")+")");
					rett=false;
					isValid=false;
				}

			}

		}

	});

	return isValid;
};

jQuery.fn.clearErrorAlert = function () {
	this.each(function () {
		var el = $(this);
		el.removeAttr("invalid").removeClass("formElementsError");
		$("#" + el.prop("id") + "error").remove();
	});
	return this;
};

jQuery.fn.createErrorAlert = function (errorCode, message) {
	this.each(function () {
		var el = $(this);
		el.attr("invalid", "true").addClass("formElementsError");
		if ($("#" + el.prop("id") + "error").length <= 0) {
			var errMess = (errorCode ? errorCode : "") + ": " + (message ? message : "");
			var err = "<span class='formElementExclamation' id=\"" + el.prop("id") + "error\" error='1'";
			err += " onclick=\"alert($(this).attr('title'))\" border='0' align='absmiddle'>&nbsp;";
			err += "</span>\n";
			err = $(err);
			err.prop("title", errMess);
			el.after(err);
		}
	});
	return this;
};


// button submit support BEGIN ------------------

function saveFormValues(idForm) {
	var formx = obj(idForm);
	formx.setAttribute("savedAction", formx.action);
	formx.setAttribute("savedTarget", formx.target);
	var el = formx.elements;
	for (i = 0; i < el.length; i++) {
		if (el[i].getAttribute("savedValue") != null) {
			el[i].setAttribute("savedValue", el[i].value);
		}
	}
}

function restoreFormValues(idForm) {
	var formx = obj(idForm);
	formx.action = formx.getAttribute("savedAction");
	formx.target = formx.getAttribute("savedTarget");
	var el = formx.elements;
	for (i = 0; i < el.length; i++) {
		if (el[i].getAttribute("savedValue") != null) {
			el[i].value = el[i].getAttribute("savedValue");
		}
	}
}

function changeActionAndSubmit(action,command){
	var f=$("form:first");
	f.prop("action",action);
	f.find("[name=CM]").val(command);
	f.submit();
}



// textarea limit size -------------------------------------------------
function limitSize(ob) {
	if (ob.getAttribute("maxlength")) {
		var ml =parseInt(ob.getAttribute("maxlength"));
		var val = ob.value;//.replace(/\r\n/g,"\n");
		if (val.length > ml) {
			ob.value = val.substr(0, ml);
			$(ob).createErrorAlert("Error",i18n.ERR_FIELD_MAX_SIZE_EXCEEDED);
		} else {
			$(ob).clearErrorAlert();
		}
	}
	return true;
}


// verify before unload BEGIN ----------------------------------------------------------------------------

function alertOnUnload(container) {
  //console.debug("alertOnUnload",container,muteAlertOnChange);
  if (!muteAlertOnChange) {

    //first try to call a function eventually defined on the page
    if (typeof(managePageUnload) == "function")
      managePageUnload();

    container=container||$("body");
    var inps= $("[alertonchange=true]",container).find("[oldValue=1]");
    for (var j = 0; j < inps.length; j++) {
      var anInput = inps.eq(j);
      //console.debug(j,anInput,anInput.isValueChanged())
      var oldValue = anInput.getOldValue() + "";
      if (!('true' == '' + anInput.attr('excludeFromAlert'))) {
        if (anInput.attr("maleficoTiny")) {
          if (tinymce.EditorManager.get(anInput.prop("id")).isDirty()) {
            return i18n.FORM_IS_CHANGED + " \"" + anInput.prop("name") + "\"";
          }

        } else if (anInput.isValueChanged()) {
          var inputLabel = $("label[for='" + anInput.prop("id") + "']").text(); //use label element
          inputLabel = inputLabel ? inputLabel : anInput.prop("name");
          return i18n.FORM_IS_CHANGED + " \"" + inputLabel + "\"";
        }
      }
    }
  }
  return undefined;
}

function canILeave(){
	var ret = window.onbeforeunload();
	if (typeof(ret)!="undefined" && !confirm(ret+"  \n"+i18n.PROCEED))
		return false;
	else
		return true;
}

// ---------------------------------- oldvalues management
// update all values selected
jQuery.fn.updateOldValue = function () {
	this.each(function () {
		var el = $(this);
		var val=(el.is(":checkbox,:radio")?el.prop("checked"):el.val())+"";
		el.data("_oldvalue", val);
	});
	return this;
};

// return true if at least one element has changed
jQuery.fn.isValueChanged = function () {
	var ret = false;
	this.each(function () {
		var el = $(this);
		var val=(el.is(":checkbox,:radio")?el.prop("checked"):el.val())+"";
		if (val != el.data("_oldvalue") + "") {
			//console.debug("io sono diverso "+el.prop("id")+ " :"+el.val()+" != "+el.data("_oldvalue"));
			ret = true;
			return false;
		}
	});
	return ret;
};

jQuery.fn.getOldValue = function () {
	return $(this).data("_oldvalue");
};

jQuery.fn.fillJsonWithInputValues = function (jsonObject) {
  var inputs = this.find(":input");
  $.each(inputs.serializeArray(),function(){
    if (this.name) {
        jsonObject[this.name] = this.value;
    }
  });

  inputs.filter(":checkbox[name]").each(function () {
    var el = $(this);
    jsonObject[el.attr("name")] = el.is(":checked") ? "yes" : "no";

  })

  return this;
};



function enlargeTextArea(immediate) {
  //console.debug("enlargeTextArea",immediate);
	var el = $(this);

  var delay=immediate===true?1:300;
	el.stopTime("taResizeApply");
	el.oneTime(delay,"taResizeApply",function(){

		var miH = el.is("[minHeight]") ? parseInt(el.attr("minHeight")) : 30;
		var maH = el.is("[maxHeight]") ? parseInt(el.attr("maxHeight")) : 400;
		var inc = el.is("[lineHeight]") ? parseInt(el.attr("lineHeight")) : 30;

    //si copiano nel css per sicurezza
    el.css({maxHeight:maH,minHeight:miH});

		var domEl = el.get(0);
		var pad = el.outerHeight()-el.height();
		//devo allargare
		if (domEl.scrollHeight>el.outerHeight() && el.outerHeight()<maH){
			var nh=domEl.scrollHeight-pad + inc;
			nh=nh>maH-pad?maH-pad:nh;
			el.height(nh);
		} else if (el.height()>miH){
			//devo stringere
			el.height(el.height()-inc);

			while(el.outerHeight()-domEl.scrollHeight > 0 && el.height()>miH){
				el.height(el.height()-inc);
			}
			var newH=domEl.scrollHeight-pad +inc;
			//newH=newH<minH?minH:newH;
			el.height(newH);

		}
		el.stopTime("winResize");
	});

}
