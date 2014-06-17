/* InstantClick 2.1 | (C) 2014 Alexandre Dieulot | http://instantclick.io/license.html */
var InstantClick = function(document, location) {
	// Internal variables
	var $currentLocationWithoutHash
	var $urlToPreload
	var $preloadTimer

	// Preloading-related variables
	var $history = {}
	var $xhr
	var $url = false
	var $title = false
	var $hasBody = true
	var $body = false
	var $timing = {}
	var $isPreloading = false
	var $isWaitingForCompletion = false

	// Variables defined by public functions
	var $useWhitelist
	var $preloadOnMousedown
	var $delayBeforePreload
	var $eventsCallbacks = {
		change: []
	}


	////////// HELPERS //////////


	function removeHash(url) {
		var index = url.indexOf('#')
		if (index < 0) {
			return url
		}
		return url.substr(0, index)
	}

	function getLinkTarget(target) {
		while (target.nodeName != 'A') {
			target = target.parentNode
		}
		return target
	}

	function triggerPageEvent(eventType) {
		for (var i = 0; i < $eventsCallbacks[eventType].length; i++) {
			$eventsCallbacks[eventType][i]()
		}
	}

	function changePage(title, body, newUrl, scrollY_) {
		var doc = document.implementation.createHTMLDocument('')
		doc.documentElement.innerHTML = body
		document.documentElement.replaceChild(doc.body, document.body)
		/* We cannot just use `document.body = doc.body` as it causes Safari 5.1, 6.0,
		   and Mobile 7.0 to execute script tags directly.
		*/

		var elem = document.createElement('i')
		elem.innerHTML = title
		document.title = elem.textContent

		if (newUrl) {
			history.pushState(null, null, newUrl)

			var hashIndex = newUrl.indexOf('#')
			var hashElem = hashIndex > -1 && document.getElementById(newUrl.substr(hashIndex + 1))
			var offset = 0
			if (hashElem) {
				for (; hashElem.offsetParent; hashElem = hashElem.offsetParent) {
					offset += hashElem.offsetTop
				}
			}
			scrollTo(0, offset)

			$currentLocationWithoutHash = removeHash(newUrl)
		}
		else {
			scrollTo(0, scrollY_)
		}

		instantanize()

		triggerPageEvent('change')
	}

	function setPreloadingAsHalted() {
		$isPreloading = false
		$isWaitingForCompletion = false
	}


	////////// EVENT HANDLERS //////////


	function mousedown(e) {
		preload(getLinkTarget(e.target).href)
	}

	function mouseover(e) {
		var a = getLinkTarget(e.target)
		a.addEventListener('mouseout', mouseout)
		if (!$delayBeforePreload) {
			preload(a.href)
		}
		else {
			$urlToPreload = a.href
			$preloadTimer = setTimeout(preload, $delayBeforePreload)
		}
	}

	function click(e) {
		if (e.which > 1 || e.metaKey || e.ctrlKey) { // Opening in new tab
			return
		}
		e.preventDefault()
		display(getLinkTarget(e.target).href)
	}

	function mouseout() {
		if ($preloadTimer) {
			clearTimeout($preloadTimer)
			$preloadTimer = false
			return
		}

		if (!$isPreloading || $isWaitingForCompletion) {
			return
		}
		$xhr.abort()
		setPreloadingAsHalted()
	}

	function readystatechange() {
		if ($xhr.readyState < 4) {
			return
		}
		if ($xhr.status == 0) {
			/* Request aborted */
			return
		}

		$timing.ready = +new Date - $timing.start

		var text = $xhr.responseText

		var titleIndex = text.indexOf('<title')
		if (titleIndex > -1) {
			$title = text.substr(text.indexOf('>', titleIndex) + 1)
			$title = $title.substr(0, $title.indexOf('</title'))
		}

		var bodyIndex = text.indexOf('<body')
		if (bodyIndex > -1) {
			$body = text.substr(bodyIndex)
			var closingIndex = $body.indexOf('</body')
			if (closingIndex > -1) {
				$body = $body.substr(0, closingIndex)
			}

			var urlWithoutHash = removeHash($url)
			$history[urlWithoutHash] = {
				body: $body,
				title: $title,
				scrollY: urlWithoutHash in $history ? $history[urlWithoutHash].scrollY : 0
			}
		}
		else {
			$hasBody = false
		}

		if ($isWaitingForCompletion) {
			$isWaitingForCompletion = false
			display($url)
		}
	}


	////////// MAIN FUNCTIONS //////////


	function instantanize(isInitializing) {
		var as = document.getElementsByTagName('a'), a, domain = location.protocol + '//' + location.host
		for (var i = as.length - 1; i >= 0; i--) {
			a = as[i]
			if (a.target || // target="_blank" etc.
				a.hasAttribute('download') ||
				a.href.indexOf(domain + '/') != 0 || // another domain (or no href attribute)
				a.href.indexOf('#') > -1 && removeHash(a.href) == $currentLocationWithoutHash || // link to an anchor
				($useWhitelist ? !a.hasAttribute('data-instant') : a.hasAttribute('data-no-instant'))) {
				continue
			}
			if ($preloadOnMousedown) {
				a.addEventListener('mousedown', mousedown)
			}
			else {
				a.addEventListener('mouseover', mouseover)
			}
			a.addEventListener('click', click)
		}
		if (!isInitializing) {
			var scripts = document.getElementsByTagName('script'), script, copy, parentNode, nextSibling
			for (i = 0, j = scripts.length; i < j; i++) {
				script = scripts[i]
				if (script.hasAttribute('data-no-instant')) {
					continue
				}
				copy = document.createElement('script')
				if (script.src) {
					copy.src = script.src
				}
				if (script.innerHTML) {
					copy.innerHTML = script.innerHTML
				}
				parentNode = script.parentNode
				nextSibling = script.nextSibling
				parentNode.removeChild(script)
				parentNode.insertBefore(copy, nextSibling)
			}
		}
	}

	function preload(url) {
		if (!$preloadOnMousedown && 'display' in $timing && +new Date - ($timing.start + $timing.display) < 100) {
			/* After a page is displayed, if the user's cursor happens to be above a link
			   a mouseover event will be in most browsers triggered automatically, and in
			   other browsers it will be triggered when the user moves his mouse by 1px.

			   Here are the behavior I noticed, all on Windows:
			   - Safari 5.1: auto-triggers after 0 ms
			   - IE 11: auto-triggers after 30-80 ms (looks like it depends on page's size)
			   - Firefox: auto-triggers after 10 ms
			   - Opera 18: auto-triggers after 10 ms

			   - Chrome: triggers when cursor moved
			   - Opera 12.16: triggers when cursor moved

			   To remedy to this, we do not start preloading if last display occurred less than
			   100 ms ago. If they happen to click on the link, they will be redirected.
			*/

			return
		}
		if ($preloadTimer) {
			$clearTimeout($preloadTimer)
			$preloadTimer = false
		}

		if (!url) {
			url = $urlToPreload
		}

		if ($isPreloading && (url == $url || $isWaitingForCompletion)) {
			return
		}
		$isPreloading = true
		$isWaitingForCompletion = false

		$url = url
		$body = false
		$hasBody = true
		$timing = {
			start: +new Date
		}
		$xhr.open('GET', url)
		$xhr.send()
	}

	function display(url) {
		if (!('display' in $timing)) {
			$timing.display = +new Date - $timing.start
		}
		if ($preloadTimer) {
			/* Happens when there’s a delay before preloading and that delay
			   hasn't expired (preloading didn't kick in).
			*/

			if ($url && $url != url) {
				/* Happens when the user clicks on a link before preloading
				   kicks in while another link is already preloading.
				*/

				location.href = url
				return
			}
			preload(url)
			$isWaitingForCompletion = true
			return
		}
		if (!$isPreloading || $isWaitingForCompletion) {
			/* If the page isn't preloaded, it likely means
			   the user has focused on a link (with his Tab
			   key) and then pressed Return, which triggered a click.
			   Because very few people do this, it isn't worth handling this
			   case and preloading on focus (also, focusing on a link
			   doesn't mean it's likely that you'll "click" on it), so we just
			   redirect them when they "click".
			   It could also mean the user hovered over a link less than 100 ms
			   after a page display, thus we didn't start the preload (see
			   comments in `preload()` for the rationale behind this.)

			   If the page is waiting for completion, the user clicked twice
			   while the page was preloading.
			   Two possibilities:
			   1) He clicks on the same link again, either because it's slow
			      to load (there's no browser loading indicator with
			      InstantClick, so he might think his click hasn't registered
			      if the page isn't loading fast enough) or because he has
			      a habit of double clicking on the web;
			   2) He clicks on another link.

			   In the first case, we redirect him (send him to the page the old
			   way) so that he can have the browser's loading indicator back.
			   In the second case, we redirect him because we haven't preloaded
			   that link, since we were already preloading the last one.

			   Determining if it's a double click might be overkill as there is
			   (hopefully) not that many people that double click on the web.
			   Fighting against the perception that the page is stuck is
			   interesting though, a seemingly good way to do that would be to
			   later incorporate a progress bar.
			*/

			location.href = url
			return
		}
		if (!$hasBody) {
			location.href = $url
			return
		}
		if (!$body) {
			$isWaitingForCompletion = true
			return
		}
		$history[$currentLocationWithoutHash].scrollY = pageYOffset
		setPreloadingAsHalted()
		changePage($title, $body, $url)
	}


	////////// PUBLIC VARIABLE AND FUNCTIONS //////////


	var supported = 'pushState' in history

	function init() {
		if ($currentLocationWithoutHash) {
			/* Already initialized */
			return
		}
		if (!supported) {
			triggerPageEvent('change')
			return
		}
		for (var i = arguments.length - 1; i >= 0; i--) {
			var arg = arguments[i]
			if (arg === true) {
				$useWhitelist = true
			}
			else if (arg == 'mousedown') {
				$preloadOnMousedown = true
			}
			else if (typeof arg == 'number') {
				$delayBeforePreload = arg
			}
		}
		$currentLocationWithoutHash = removeHash(location.href)
		$history[$currentLocationWithoutHash] = {
			body: document.body.outerHTML,
			title: document.title,
			scrollY: pageYOffset
		}
		$xhr = new XMLHttpRequest()
		$xhr.addEventListener('readystatechange', readystatechange)

		instantanize(true)

		triggerPageEvent('change')

		addEventListener('popstate', function() {
			var loc = removeHash(location.href)
			if (loc == $currentLocationWithoutHash) {
				return
			}
			if (!(loc in $history)) {
				location.href = location.href // Reloads the page and makes use of cache for assets, unlike location.reload()
				return
			}
			$history[$currentLocationWithoutHash].scrollY = pageYOffset
			$currentLocationWithoutHash = loc
			changePage($history[loc].title, $history[loc].body, false, $history[loc].scrollY)
		})
	}

	function on(eventType, callback) {
		$eventsCallbacks[eventType].push(callback)
	}

	/* The debug function isn't included by default to reduce file size.
	   To enable it, add a slash at the beginning of the comment englobing
	   the debug function, and uncomment "debug: debug," in the return
	   statement below the function. */

	/*
	function debug() {
		return {
			currentLocationWithoutHash: $currentLocationWithoutHash,
			history: $history,
			xhr: $xhr,
			url: $url,
			title: $title,
			hasBody: $hasBody,
			body: $body,
			timing: $timing,
			isPreloading: $isPreloading,
			isWaitingForCompletion: $isWaitingForCompletion
		}
	}
	//*/


	return {
		// debug: debug,
		supported: supported,
		init: init,
		on: on
	}

}(document, location);
