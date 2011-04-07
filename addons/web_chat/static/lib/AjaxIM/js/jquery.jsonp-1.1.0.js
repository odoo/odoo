/*
 * jQuery JSONP Core Plugin 1.1.0 (2009-10-06)
 * 
 * http://code.google.com/p/jquery-jsonp/
 *
 * Copyright (c) 2009 Julian Aubourg
 *
 * This document is licensed as free software under the terms of the
 * MIT License: http://www.opensource.org/licenses/mit-license.php
 */
(function($){
	
	// ###################### UTILITIES ##
	// Test a value is neither undefined nor null
	var defined = function(v) {
		return v!==undefined && v!==null;
	},
	// Call if defined
	callIfDefined = function(method,object,parameters) {
		defined(method) && method.apply(object,parameters);
	},
	// Let the current thread running
	later = function(functor) {
		setTimeout(functor,0);
	},
	// String constants (for better minification)
	empty="",
	amp="&",
	qMark="?",
	success = "success",
	error = "error",
	
	// Head element (for faster use)
	head = $("head"),
	// Page cache
	pageCache = {},
	
	// ###################### DEFAULT OPTIONS ##
	xOptionsDefaults = {
		//beforeSend: undefined,
		//cache: false,
		callback: "C",
		//callbackParameter: undefined,
		//complete: undefined,
		//data: ""
		//dataFilter: undefined,
		//error: undefined,
		//pageCache: false,
		//success: undefined,
		//timeout: 0,		
		url: location.href
	},

	// ###################### MAIN FUNCTION ##
	jsonp = function(xOptions) {
		
		// Build data with default
		xOptions = $.extend({},xOptionsDefaults,xOptions);
		
		// References to beforeSend (for better minification) 
		var beforeSendCallback = xOptions.beforeSend,
		
		// Abort/done flag
		done = 0;
		
		// Put a temporary abort
		xOptions.abort = function() { done = 1; };

		// Call beforeSend if provided (early abort if false returned)
		if (defined(beforeSendCallback) && (beforeSendCallback(xOptions,xOptions)===false || done))
			return xOptions;

		// References to xOptions members (for better minification)
		var successCallback = xOptions.success,
		completeCallback = xOptions.complete,
		errorCallback = xOptions.error,
		dataFilter = xOptions.dataFilter,
		callbackParameter = xOptions.callbackParameter,
		successCallbackName = xOptions.callback,
		cacheFlag = xOptions.cache,
		pageCacheFlag = xOptions.pageCache,
		url = xOptions.url,
		data = xOptions.data,
		timeout = xOptions.timeout,

		// Misc variables
		splitUrl,splitData,i,j;		
		
		// Control entries
		url = defined(url)?url:empty;
		data = defined(data)?((typeof data)=="string"?data:$.param(data)):empty;
		
		// Add callback parameter if provided as option
		defined(callbackParameter)
			&& (data += (data==empty?empty:amp)+escape(callbackParameter)+"=?");
		
		// Add anticache parameter if needed
		!cacheFlag && !pageCacheFlag
			&& (data += (data==empty?empty:amp)+"_"+(new Date()).getTime()+"=");
		
		// Search for ? in url
		splitUrl = url.split(qMark);
		// Also in parameters if provided
		// (and merge arrays)
		if (data!=empty) {
			splitData = data.split(qMark);
			j = splitUrl.length-1;
			j && (splitUrl[j] += amp + splitData.shift());
			splitUrl = splitUrl.concat(splitData);
		}
		// If more than 2 ? replace the last one by the callback
		i = splitUrl.length-2;
		i && (splitUrl[i] += successCallbackName + splitUrl.pop());
		
		// Build the final url
		var finalUrl = splitUrl.join(qMark),
		
		// Utility function
		notifySuccess = function(json) {
			// Apply the data filter if provided
			defined(dataFilter) && (json = dataFilter.apply(xOptions,[json]));
			// Call success then complete
			callIfDefined(successCallback,xOptions,[json,success]);
			callIfDefined(completeCallback,xOptions,[xOptions,success]);
		},
	    notifyError = function(type) {
			// Call error then complete
			callIfDefined(errorCallback,xOptions,[xOptions,type]);
			callIfDefined(completeCallback,xOptions,[xOptions,type]);
	    },
	    
	    // Get from pageCache
	    pageCached = pageCache[finalUrl];
		
		// Check page cache
		if (pageCacheFlag && defined(pageCached)) {
			later(function() {
				// If an error was cached
				defined(pageCached.s)
				? notifySuccess(pageCached.s)
				: notifyError(error);
			});
			return xOptions;
		}
		
		
		// Create & write to the iframe (sends the request)
		// We let the hand to current code to avoid
		// pre-emptive callbacks
		
		// We also install the timeout here to avoid
		// timeout before the code has been dumped to the frame
		// (in case of insanely short timeout values)
		later(function() {
			
			// If it has been aborted, do nothing
			if (done) return;
		
			// Create an iframe & add it to the document
			var frame = $("<iframe />").appendTo(head),
			
			// Get the iframe's window and document objects
			tmp = frame[0],
			window = tmp.contentWindow || tmp.contentDocument,
			document = window.document,
			
			// Declaration of cleanup function
			cleanUp,
			
			// Declaration of timer for timeout (so we can clear it eventually)
			timeoutTimer,
			
			// Error function
			errorFunction = function (_,type) {
				// If pure error (not timeout), cache if needed
				pageCacheFlag && !defined(type) && (pageCache[finalUrl] = empty); 
				// Cleanup
				cleanUp();
				// Call error then complete
				notifyError(defined(type)?type:error);
			},
			
			// Iframe variable cleaning function
			removeVariable = function(varName) {
				window[varName] = undefined;
				try { delete window[varName]; } catch(_) {}
			},
			
			// Error callback name
			errorCallbackName = successCallbackName=="E"?"X":"E";
			
			// Control if we actually retrieved the document
			if(!defined(document)) {
				document = window;
			    window = document.getParentNode();
			}
			
			// We have to open the document before
			// declaring variables in the iframe's window
			// Don't ask me why, I have no clue
			document.open();
			
			// Install callbacks
			window[successCallbackName] = function(json) {
				// Set as treated
				done = 1;
				// Pagecache is needed
				pageCacheFlag && (pageCache[finalUrl] = {s: json});
				// Give hand back to frame
				// To finish gracefully
				later(function(){
					// Cleanup
					cleanUp();
					// Call success then complete
					notifySuccess(json);
				});
			};
			
			window[errorCallbackName] = function(state) {
				// If not treated, mark
				// then give hand back to iframe
				// for it to finish gracefully
				(!state || state=="complete") && !done++ && later(errorFunction);
			};
			
			// Clean up function (declaration)
			xOptions.abort = cleanUp = function() {
				// Clear the timeout (is it exists)
				clearTimeout(timeoutTimer);
				// Open the iframes document & clean
				document.open();
				removeVariable(errorCallbackName);
				removeVariable(successCallbackName);
				document.write(empty);
				document.close();
				frame.remove();
			};
		
			// Write to the document
			document.write([
				'<html><head><script src="',
				finalUrl,'" onload="',
				errorCallbackName,'()" onreadystatechange="',
				errorCallbackName,'(this.readyState)"></script></head><body onload="',
				errorCallbackName,'()"></body></html>'
			].join(empty)
			);
			
			// Close (makes some browsers happier)
			document.close();
			
			// If a timeout is needed, install it
			timeout>0 && (timeoutTimer = setTimeout(function(){
					!done && errorFunction(empty,"timeout");
			},timeout));
		});
		
		return xOptions;
	}
	
	// ###################### SETUP FUNCTION ##
	jsonp.setup = function(xOptions) {
		$.extend(xOptionsDefaults,xOptions);
	};

	// ###################### INSTALL in jQuery ##
	$.jsonp = jsonp;
	
})(jQuery);