### WARNING
**This `master` branch contains the `v2.x` codebase for ZeroClipboard! For the `v1.x` codebase, see the [`1.x-master`](https://github.com/zeroclipboard/zeroclipboard/tree/1.x-master) branch instead.**


# ZeroClipboard
[![GitHub Latest Release](https://badge.fury.io/gh/zeroclipboard%2Fzeroclipboard.png)](https://github.com/zeroclipboard/zeroclipboard) [![Build Status](https://secure.travis-ci.org/zeroclipboard/zeroclipboard.png?branch=master)](https://travis-ci.org/zeroclipboard/zeroclipboard) [![Coverage Status](https://coveralls.io/repos/zeroclipboard/zeroclipboard/badge.png?branch=master)](https://coveralls.io/r/zeroclipboard/zeroclipboard?branch=master) [![Dependency Status](https://david-dm.org/zeroclipboard/zeroclipboard.png?theme=shields.io)](https://david-dm.org/zeroclipboard/zeroclipboard) [![Dev Dependency Status](https://david-dm.org/zeroclipboard/zeroclipboard/dev-status.png?theme=shields.io)](https://david-dm.org/zeroclipboard/zeroclipboard#info=devDependencies)

The ZeroClipboard library provides an easy way to copy text to the clipboard using an invisible [Adobe Flash](http://en.wikipedia.org/wiki/Adobe_Flash) movie and a [JavaScript](http://en.wikipedia.org/wiki/JavaScript) interface. The "Zero" signifies that the library is invisible and the user interface is left entirely up to you. 

This is achieved by automatically floating the invisible movie on top of a [DOM](http://en.wikipedia.org/wiki/Document_Object_Model) element of your choice. Standard mouse events are even propagated out to your DOM element, so you can still have rollover and mousedown effects.


## Limitations

### User Interaction Required

Due to browser and Flash security restrictions, this clipboard injection can _**ONLY**_ occur when
the user clicks on the invisible Flash movie. A simulated `click` event from JavaScript will not
suffice as this would enable [clipboard poisoning](http://www.computerworld.com/s/article/9117268/Adobe_patches_Flash_clickjacking_and_clipboard_poisoning_bugs).

### Other Limitations

For a complete list of limitations, see [docs/instructions.md#limitations](docs/instructions.md#limitations).


## Simple Example

```html
<html>
  <body>
    <button id="copy-button" data-clipboard-text="Copy Me!" title="Click to copy me.">Copy to Clipboard</button>
    <script src="ZeroClipboard.js"></script>
    <script src="main.js"></script>
  </body>
</html>
```

```js
// main.js
var client = new ZeroClipboard( document.getElementById("copy-button") );

client.on( "ready", function( readyEvent ) {
  // alert( "ZeroClipboard SWF is ready!" );

  client.on( "aftercopy", function( event ) {
    // `this` === `client`
    // `event.target` === the element that was clicked
    event.target.style.display = "none";
    alert("Copied text to clipboard: " + event.data["text/plain"] );
  } );
} );
```

See [docs/instructions.md](docs/instructions.md) for more advanced options in using the library on your site.
See [docs/api/ZeroClipboard.md](docs/api/ZeroClipboard.md) for the complete API documentation.

Here is a working [test page](http://zeroclipboard.org/#demo) where you can try out ZeroClipboard in your browser.


## Testing ZeroClipboard Locally

To test the page [demo page](http://zeroclipboard.org/#demo) locally, clone the [website repo](https://github.com/zeroclipboard/zeroclipboard.org).


## Support

This library is fully compatible with Flash Player 11.0.0 and above, which requires
that the clipboard copy operation be initiated by a user click event inside the
Flash movie. This is achieved by automatically floating the invisible movie on top
of a [DOM](http://en.wikipedia.org/wiki/Document_Object_Model) element of your
choice. Standard mouse events are even propagated out to your DOM element, so you
can still have rollover and mousedown effects with just a _little_ extra effort.

ZeroClipboard `v2.x` is expected to work in IE9+ and all of the evergreen browsers.


## Contributing

see [CONTRIBUTING.md](CONTRIBUTING.md)


## Releases

Starting with version [1.1.7](https://github.com/zeroclipboard/zeroclipboard/releases/tag/v1.1.7), ZeroClipboard uses [semantic versioning](http://semver.org/).

see [releases](https://github.com/zeroclipboard/zeroclipboard/releases)


## Roadmap

see [roadmap.md](docs/roadmap.md)
