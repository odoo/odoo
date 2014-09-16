# Security

We try our best to keep ZeroClipboard secure but there are some rules that you should consider following to keep your site safe.


## Existing Configuration

For the existing configuration options available for security, see [Configuration Options](api/ZeroClipboard.md#configuration-options).


## Rules

Basically, if an attacker gets access to the main window/global object via an XSS exploit, it's pretty much an instant "GAME OVER" unless **ALL** of the following are true:
 1. The `ZeroClipboard` object itself is not globally accessible.
 2. The `ZeroClipboard.prototype` object itself is not globally accessible.
 3. No `ZeroClipboard` instances are globally accessible.
 4. No callback functions for dispatched ZeroClipboard events are globally accessible.
 5. If a variable is used to set the path to the SWF via `ZeroClipboard.config`, that variable must not be globally accessible.
 6. The DOM is not accessible (due to built-in support for `data-clipboard-text` and `data-clipboard-target` attributes).

 
## Examples

 1. Having `ZeroClipboard` instances globally accessible (versus encapsulated in a closure). This allows an attacker to manually call a client's `setText` method and inject their own text.
 2. As with all globally accessible functions in JavaScript, any globally accessible callback functions (hooked to events) can be overridden by an attacker. This isn't terribly dangerous but could be annoying.
 3. Overriding any of the `ZeroClipboard` or `ZeroClipboard.prototype` properties or methods, if globally accessible.
 4. Adding `data-clipboard-text` or `data-clipboard-target` attributes to every element in the DOM.

 
### Responsible Disclosure

If you find any security holes that you believe can be patched, please submit a pull request or file an issue. We will be very appreciative!
