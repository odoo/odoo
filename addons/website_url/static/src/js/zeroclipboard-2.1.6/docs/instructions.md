### WARNING
**This `master` branch contains the `v2.x` codebase for ZeroClipboard! For the `v1.x` codebase, see the [`1.x-master`](https://github.com/zeroclipboard/zeroclipboard/tree/1.x-master) branch instead.**


# Overview

The ZeroClipboard library provides an easy way to copy text to the clipboard using an invisible [Adobe Flash](http://en.wikipedia.org/wiki/Adobe_Flash) movie and a [JavaScript](http://en.wikipedia.org/wiki/JavaScript) interface. The "Zero" signifies that the library is invisible and the user interface is left entirely up to you. 

This is achieved by automatically floating the invisible movie on top of a [DOM](http://en.wikipedia.org/wiki/Document_Object_Model) element of your choice. Standard mouse events are even propagated out to your DOM element, so you can still have rollover and mousedown effects.


## Limitations

### User Interaction Required

Due to browser and Flash security restrictions, this clipboard injection can _**ONLY**_ occur when
the user clicks on the invisible Flash movie. A simulated `click` event from JavaScript will not
suffice as this would enable [clipboard poisoning](http://www.computerworld.com/s/article/9117268/Adobe_patches_Flash_clickjacking_and_clipboard_poisoning_bugs).

### Synchronicity Required During `copy`

If a handler of `copy` event intends to modify the pending data for clipboard
injection, it _MUST_ operate synchronously in order to maintain the temporarily elevated
permissions granted by the user's `click` event. The most common "gotcha" for this restriction is
if someone wants to make an asynchronous XMLHttpRequest in response to the `copy` event to get the
data to inject &mdash; this will not work. You must make it a _synchronous_ XMLHttpRequest instead, or do the
work in advance before the `copy` event is fired.

### OS-Specific Limitations

See [OS Considerations](#os-considerations) below.


## Installation

### [NPM](https://www.npmjs.org/) [![NPM version](https://badge.fury.io/js/zeroclipboard.png)](https://www.npmjs.org/package/zeroclipboard)

```shell
npm install zeroclipboard
```

### [Bower](http://bower.io/) [![Bower version](https://badge.fury.io/bo/zeroclipboard.png)](http://bower.io/search/?q=zeroclipboard)

```shell
bower install zeroclipboard
```

### [SPM](http://spmjs.io/) [![SPM version](http://spmjs.io/badge/zeroclipboard)](http://spmjs.io/package/zeroclipboard)

```shell
spm install zeroclipboard
```

### [PHP Composer](https://getcomposer.org/) [![PHP version](https://badge.fury.io/ph/zeroclipboard%2Fzeroclipboard.svg)](https://packagist.org/packages/zeroclipboard/zeroclipboard)

For any PHP Composer users, ZeroClipboard is also [available on Packagist](https://packagist.org/packages/zeroclipboard/zeroclipboard).

### [Ruby Gem](https://rubygems.org/)

For any Rails users, the [`zeroclipboard-rails` Ruby Gem](https://rubygems.org/gems/zeroclipboard-rails) is available to automatically add ZeroClipboard into your Rails asset pipeline.


## CDN Availability

If you'd like to use ZeroClipboard hosted via a CDN (content delivery network), you can try:

 - **cdnjs**: http://cdnjs.com/libraries/zeroclipboard
 - **jsDelivr**: http://www.jsdelivr.com/#!zeroclipboard


## Setup

To use the library, simply include the following JavaScript file in your page:

```html
<script type="text/javascript" src="ZeroClipboard.js"></script>
```

You also need to have the "`ZeroClipboard.swf`" file available to the browser.  If this file is
located in the same directory as your web page, then it will work out of the box.  However, if the
SWF file is hosted elsewhere, you need to set the URL like this (place this code _after_ the script
tag):

```js
ZeroClipboard.config( { swfPath: "http://YOURSERVER/path/ZeroClipboard.swf" } );
```


## Clients

Now you are ready to create one or more _clients_.  A client is a single instance of the clipboard
library on the page, linked to one or more DOM elements. Here is how to create a client instance:

```js
var client = new ZeroClipboard();
```

You can also include an element or array of elements in the new client. _\*\*This example uses jQuery to find "copy buttons"._

```js
var client = new ZeroClipboard($(".copy-button"));
```


## API

For the full API documentation, see [api/ZeroClipboard.md](api/ZeroClipboard.md). The full set of
[Configuration Options](api/ZeroClipboard.md#configuration-options) are also documented there.

For developers who want to wrap ZeroClipboard into a 3rd party plugin
(e.g. [jquery.zeroclipboard](https://github.com/zeroclipboard/jquery.zeroclipboard)),
see the [api/ZeroClipboard.Core.md](api/ZeroClipboard.Core.md) documentation instead.


### Text To Copy

Setting the clipboard text can be done in 4 ways:

1. Add a `copy` event handler in which you call `event.clipboardData.setData` to set the appropriate data. This event is triggered every time ZeroClipboard tries to inject into the clipboard. Example:

   ```js
   client.on( "copy", function (event) {
      var clipboard = event.clipboardData;
      clipboard.setData( "text/plain", "Copy me!" );
      clipboard.setData( "text/html", "<b>Copy me!</b>" );
      clipboard.setData( "application/rtf", "{\\rtf1\\ansi\n{\\b Copy me!}}" );
   });
   ```

2. Set the "text/plain" [and _usually_ "text/html"] clipboard segments via `data-clipboard-target` attribute on the button. ZeroClipboard will look for the target element via ID and try to get the HTML value via `.value`, `.outerHTML`, or `.innerHTML`, and the text value via `.value`, `.textContent`, or `.innerText`. If the HTML and text values for the targeted element match, the value will only be placed into the "text/plain" segment of the clipboard (i.e. the "text/html" segment will cleared).

  ```html
  <button id="my-button_text" data-clipboard-target="clipboard_text">Copy to Clipboard</button>
  <button id="my-button_textarea" data-clipboard-target="clipboard_textarea">Copy to Clipboard</button>
  <button id="my-button_pre" data-clipboard-target="clipboard_pre">Copy to Clipboard</button>

  <input type="text" id="clipboard_text" value="Clipboard Text"/>
  <textarea id="clipboard_textarea">Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod
  tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
  quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
  consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
  cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non
  proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</textarea>
  <pre id="clipboard_pre">Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod
  tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
  quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
  consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
  cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non
  proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</pre>
  ```

3. Set the "text/plain" clipboard segment via `data-clipboard-text` attribute on the button. Doing this will let ZeroClipboard take care of the rest.

  ```html
  <button id="my-button" data-clipboard-text="Copy me!">Copy to Clipboard</button>
  ```

4. Set the data via the `ZeroClipboard.setData` (any segment) method.  You can call this function at any time: when the page first loads, or later like in a `copy` event handler.  Example:

  ```js
  ZeroClipboard.setData( "text/plain", "Copy me!" );
  ```

  The important caveat of using `ZeroClipboard.setData` is that the data it sets is **transient** and _will only be used for a single copy operation_. As such, we do not particularly
  recommend using `ZeroClipboard.setData` (and friends) other than inside of a `copy` event handler; however, the API will not prevent you from using it in other ways.

5. Set the data via the `client.setText` ("text/plain" segment), `client.setHtml` ("text/html" segment), `client.setRichText` ("application/rtf" segment), or `client.setData` (any segment) methods.  You can call this function at any time: when the page first loads, or later like in a `copy` event handler.  Example:

  ```js
  client.setText( "Copy me!" );
  ```

  The important caveat of using `client.setData` (and friends) is that the data it sets is **transient** and _will only be used for a single copy operation_. As such, we do not particularly
  recommend using `client.setData` (and friends) other than inside of a `copy` event handler; however, the API will not prevent you from using it in other ways.


### Clipping

Clipping refers to the process of "linking" the Flash movie to a DOM element on the page. Since the Flash movie is completely transparent, the user sees nothing out of the ordinary.

The Flash movie receives the click event and copies the text to the clipboard.  Also, mouse actions like hovering and `mousedown` generate events that you can capture (see [_Event Handlers_](#event-handlers) below).

To clip elements, you must pass an element, or array of elements to the `clip` function.

Here is how to clip your client library instance to a DOM element:

```js
client.clip( document.getElementById("d_clip_button") );
```

You can pass in a reference to the actual DOM element object itself or an array of DOM objects.  The rest all happens automatically: the movie is created, all your options set, and it is floated above the element, awaiting clicks from the user.


### Example Implementation

```html
<button id="my-button" data-clipboard-text="Copy me!" title="Click to copy to clipboard.">Copy to Clipboard</button>
```

And the code:

```js
var client = new ZeroClipboard( $("button#my-button") );
```


## CSS Effects

Since the Flash movie is floating on top of your DOM element, it will receive all the mouse events before the browser has a chance to catch them.  However, for convenience, these events are passed through to your clipboard client which you can capture (see _Event Handlers_ below), so long as the `bubbleEvents` configuration property remains set to `true`.

In addition to this, ZeroClipboard can also manage CSS classes on the clipped elements that mimic the CSS pseudo-classes ":hover" and ":active" on your DOM element.  This essentially allows your elements to behave normally, even though the floating Flash movie is the first object receiving all the mouse events during the event bubbling phase.  These "pseudo-pseudo-class" names are configurable via the `hoverClass` and `activeClass` configuration properties.

Example CSS, targeting a DOM element with a class of "clip_button":

```css
  .clip_button {
    width: 150px;
    text-align: center;
    border: 1px solid black;
    background-color: #ccc;
    margin: 10px;
    padding: 10px;
  }
  .clip_button.zeroclipboard-is-hover { background-color: #eee; }
  .clip_button.zeroclipboard-is-active { background-color: #aaa; }
```


## Examples

The following are complete, working examples of using the clipboard client library in HTML pages.


### Minimal Example

Here is a quick example using as few calls as possible:

```html
<html>
  <body>
    <div id="d_clip_button" class="clip_button" data-clipboard-text="Copy Me!" title="Click to copy." style="border:1px solid black; padding:20px;">Copy To Clipboard</div>

    <script type="text/javascript" src="ZeroClipboard.js"></script>
    <script type="text/javascript">
      var client = new ZeroClipboard( document.getElementById('d_clip_button') );
    </script>
  </body>
</html>
```

When clicked, the text "Copy me!" will be copied to the clipboard.


### A More Complete Example

Here is a more complete example which exercises many of the configuration options and event handlers:

```html
<html>
  <head>
    <style type="text/css">
      .clip_button {
        text-align: center;
        border: 1px solid black;
        background-color: #ccc;
        margin: 10px;
        padding: 10px;
      }
      .clip_button.zeroclipboard-is-hover { background-color: #eee; }
      .clip_button.zeroclipboard-is-active { background-color: #aaa; }
    </style>
  </head>
  <body>
    <script type="text/javascript" src="//ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js"></script>
    <script type="text/javascript" src="ZeroClipboard.js"></script>

    <div class="clip_button">Copy To Clipboard</div>
    <div class="clip_button">Copy This Too!</div>

    <script type="text/javascript">
      var client = new ZeroClipboard( $('.clip_button') );

      client.on( 'ready', function(event) {
        // console.log( 'movie is loaded' );

        client.on( 'copy', function(event) {
          event.clipboardData.setData('text/plain', event.target.innerHTML);
        } );

        client.on( 'aftercopy', function(event) {
          console.log('Copied text to clipboard: ' + event.data['text/plain']);
        } );
      } );

      client.on( 'error', function(event) {
        // console.log( 'ZeroClipboard error of type "' + event.name + '": ' + event.message );
        ZeroClipboard.destroy();
      } );
    </script>
  </body>
</html>
```


## Namespacing ZeroClipboard

ZeroClipboard creates DOM elements with pre-configured attributes, e.g. a `div` element with an ID of `"global-zeroclipboard-html-bridge"` to encapsulate the Flash object.

If you have a need to change the default values, they can be configured by passing in values for `containerId`, `containerClass`, and/or `swfObjectId` using the `ZeroClipboard.config` method. Configuration of these values is completely optional. These values cannot be reconfigured while the ZeroClipboard SWF is actively embedded, and so are completely ignored during that time.

Values for `containerId` and `swfObjectId` are validated against the [HTML4 spec for `ID` and `Name` tokens][valid_ids].

  
## AMD

If using [AMD](https://github.com/amdjs/amdjs-api/wiki/AMD) with a library such as [RequireJS](http://requirejs.org/), etc., you shouldn't need to do any special configuration for ZeroClipboard to work correctly as an AMD module.


## CommonJS

If using [CommonJS](http://wiki.commonjs.org/wiki/Modules/1.1) with a library such as [Browserify](http://browserify.org/), [Webmake](https://github.com/medikoo/modules-webmake), etc., you shouldn't need to do any special configuration for ZeroClipboard to work correctly as an CommonJS module.


## Known Conflicts With Other Libraries

### [IE freezes when clicking a ZeroClipboard clipped element within a Bootstrap Modal](https://github.com/zeroclipboard/zeroclipboard/issues/159).
 - **Cause:** Bootstrap's Modal has an `enforceFocus` function that tries to keep the focus on the modal.
   However, since the ZeroClipboard container is an immediate child of the `body`, this enforcement conflicts. Note that
   this workaround actually _overrides_ a core Bootstrap Modal function, and as such must be kept in sync as this function
   changes in future versions of Bootstrap.
 - **Workaround:** _Targeted against [Bootstrap v3.x](https://github.com/twbs/bootstrap/blob/96a9e1bae06cb21f8cf72ec528b8e31b6ab27272/js/modal.js#L115-123)._

#### Workaround A

```js
if (/MSIE|Trident/.test(window.navigator.userAgent)) {
  (function($) {
    var zcContainerId = ZeroClipboard.config('containerId');
    $('#' + zcContainerId).on('focusin', false);
  })(window.jQuery);
}
```

#### Workaround B

```js
if (/MSIE|Trident/.test(window.navigator.userAgent)) {
  (function($) {
    var zcClass = '.' + ZeroClipboard.config('containerClass');
    var proto = $.fn.modal.Constructor.prototype;
    proto.enforceFocus = function() {
      $(document)
        .off('focusin.bs.modal')  /* Guard against infinite focus loop */
        .on('focusin.bs.modal', $.proxy(function(e) {
          if (this.$element[0] !== e.target &&
             !this.$element.has(e.target).length &&
             /* Adding this final condition check is the only real change */
             !$(e.target).closest(zcClass).length
          ) {
            this.$element.focus();
          }
        }, this));
    };
  })(window.jQuery);
}
```


### [IE freezes when clicking a ZeroClipboard clipped element within a jQuery UI [Modal] Dialog](https://github.com/zeroclipboard/zeroclipboard/issues/159).
 - **Cause:** jQuery UI's Dialog (with `{ modal: true }` set) has a `_keepFocus` function that tries to keep the focus on the modal.
   However, since the ZeroClipboard container is an immediate child of the `body`, this enforcement conflicts. Luckily, jQuery UI offers
   more natural extension points than Bootstrap, so the workaround is smaller and less likely to be broken in future versions.
 - **Workaround:** _Targeted against [jQuery UI v1.10.x](https://github.com/jquery/jquery-ui/blob/457b275880b63b05b16b7c9ee6c22f29f682ebc8/ui/jquery.ui.dialog.js#L695-703)._

```js
if (/MSIE|Trident/.test(window.navigator.userAgent)) {
  (function($) {
    var zcClass = '.' + ZeroClipboard.config('containerClass');
    $.widget( 'ui.dialog', $.ui.dialog, {
      _allowInteraction: function( event ) {
        return this._super(event) || $( event.target ).closest( zcClass ).length;
      }
    } );
  })(window.jQuery);
}
```


## Support

This library is fully compatible with Flash Player 11.0.0 and above, which requires
that the clipboard copy operation be initiated by a user click event inside the
Flash movie. This is achieved by automatically floating the invisible movie on top
of a [DOM](http://en.wikipedia.org/wiki/Document_Object_Model) element of your
choice. Standard mouse events are even propagated out to your DOM element, so you
can still have rollover and mousedown effects with just a _little_ extra effort.

ZeroClipboard `v2.x` is expected to work in IE9+ and all of the evergreen browsers.



## OS Considerations

Because ZeroClipboard will be interacting with your users' system clipboards, there are some special considerations
specific to the users' operating systems that you should be aware of. With this information, you can make informed
decisions of how _your_ site should handle each of these situations.

 - **Windows:**
     - If you want to ensure that your Windows users will be able to paste their copied text into Windows
       Notepad and have it honor line breaks, you'll need to ensure that the text uses the sequence `\r\n` instead of
       just `\n` for line breaks.  If the text to copy is based on user input (e.g. a `textarea`), then you can achieve
       this transformation by utilizing the `copy` event handler, e.g.  

      ```js
      client.on('copy', function(event) {
          var text = document.getElementById('yourTextArea').value;
          var windowsText = text.replace(/\n/g, '\r\n');
          event.clipboardData.setData('text/plain', windowsText);
      });
      ```

 - **Linux:**
     - The Linux Clipboard system (a.k.a. "Selection Atoms" within the [X Consortium's Standard Inter-Client Communication Conventions Manual](http://www.x.org/docs/ICCCM/icccm.pdf)) is a complex but capable setup. However,
     for normal end users, it stinks. Flash Player's Clipboard API can either:
         1. Insert plain text into the "System Clipboard" and have it available everywhere; or
         2. Insert plain, HTML, and RTF text into the "Desktop Clipboard" but it will only be available in applications whose UI are managed by the Desktop Manager System (e.g. GNOME, etc.). This, for example, means that a user on a typical Linux configuration would not be able to paste something copied with ZeroClipboard into a terminal shell but they may still be able to paste it into OpenOffice, the browser, etc.

      As such, the default behavior for ZeroClipboard while running on Linux is to only inject plain text into the "System Clipboard" to cover the most bases.  If you want to ignore that caution and use the "Desktop Clipboard" anyway, just set the `forceEnhancedClipboard` configuration option to `true`, i.e.:

      ```js
      ZeroClipboard.config({
        forceEnhancedClipboard: true
      });
      ```




[valid_ids]: http://www.w3.org/TR/html4/types.html#type-id "HTML4 specification for `ID` and `Name` tokens"
