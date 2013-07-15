#About
**jQuery Hotkeys** is a plug-in that lets you easily add and remove handlers for keyboard events anywhere in your code supporting almost any key combination.  

This plugin is based off of the plugin by Tzury Bar Yochay: [jQuery.hotkeys](http://github.com/tzuryby/hotkeys)

The syntax is as follows:

    $(expression).bind(types, keys, handler);
    $(expression).unbind(types, handler);
    
    $(document).bind('keydown', 'ctrl+a', fn);
    
    // e.g. replace '$' sign with 'EUR'
    $('input.foo').bind('keyup', '$', function(){
      this.value = this.value.replace('$', 'EUR');
    });

## Types
Supported types are `'keydown'`, `'keyup'` and `'keypress'`

## Notes

If you want to use more than one modifiers (e.g. alt+ctrl+z) you should define them by an alphabetical order e.g. alt+ctrl+shift

Hotkeys aren't tracked if you're inside of an input element (unless you explicitly bind the hotkey directly to the input). This helps to avoid conflict with normal user typing.

## jQuery Compatibility

Works with jQuery 1.4.2 and newer.

It known to be working with all the major browsers on all available platforms (Win/Mac/Linux)

 * IE 6/7/8
 * FF 1.5/2/3
 * Opera-9
 * Safari-3
 * Chrome-0.2

### Addendum

Firefox is the most liberal one in the manner of letting you capture all short-cuts even those that are built-in in the browser such as `Ctrl-t` for new tab, or `Ctrl-a` for selecting all text. You can always bubble them up to the browser by returning `true` in your handler.

Others, (IE) either let you handle built-in short-cuts, but will add their functionality after your code has executed. Or (Opera/Safari) will *not* pass those events to the DOM at all.

*So, if you bind `Ctrl-Q` or `Alt-F4` and your Safari/Opera window is closed don't be surprised.*
