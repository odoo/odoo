`es5-shim.js` and `es5-shim.min.js` monkey-patch a JavaScript context to
contain all EcmaScript 5 methods that can be faithfully emulated with a
legacy JavaScript engine.

`es5-sham.js` and `es5-sham.min.js` monkey-patch other ES5 methods as
closely as possible.  For these methods, as closely as possible to ES5
is not very close.  Many of these shams are intended only to allow code
to be written to ES5 without causing run-time errors in older engines.
In many cases, this means that these shams cause many ES5 methods to
silently fail.  Decide carefully whether this is what you want.


## Tests

The tests are written with the Jasmine BDD test framework.
To run the tests, navigate to <root-folder>/tests/. 

In order to run against the shim-code, the tests attempt to kill the current 
implementation of the missing methods. This happens in <root-folder>/tests/helpers/h-kill.js.
So in order to run the tests against the built-in methods, invalidate that file somehow
(comment-out, delete the file, delete the script-tag, etc.).

## Shims

### Complete tests ###

* Array.prototype.every
* Array.prototype.filter
* Array.prototype.forEach
* Array.prototype.indexOf
* Array.prototype.lastIndexOf
* Array.prototype.map
* Array.prototype.some
* Array.prototype.reduce
* Array.prototype.reduceRight
* Array.isArray
* Date.now
* Date.prototype.toJSON
* Function.prototype.bind
    * :warning: Caveat: the bound function's length is always 0.
    * :warning: Caveat: the bound function has a prototype property.
    * :warning: Caveat: bound functions do not try too hard to keep you
      from manipulating their ``arguments`` and ``caller`` properties.
    * :warning: Caveat: bound functions don't have checks in ``call`` and
      ``apply`` to avoid executing as a constructor.
* Number.prototype.toFixed
* Object.keys
* String.prototype.split
* String.prototype.trim
* Date.parse (for ISO parsing)
* Date.prototype.toISOString

## Shams

* :warning: Object.create

    For the case of simply "begetting" an object that inherits
    prototypically from another, this should work fine across legacy
    engines.

    :warning: Object.create(null) will work only in browsers that
    support prototype assignment.  This creates an object that does not
    have any properties inherited from Object.prototype.  It will
    silently fail otherwise.

    :warning: The second argument is passed to Object.defineProperties
    which will probably fail either silently or with extreme predudice.

* :warning: Object.getPrototypeOf

    This will return "undefined" in some cases.  It uses `__proto__` if
    it's available.  Failing that, it uses constructor.prototype, which
    depends on the constructor property of the object's prototype having
    not been replaced.  If your object was created like this, it won't
    work:

        function Foo() {
        }
        Foo.prototype = {};

    Because the prototype reassignment destroys the constructor
    property.

    This will work for all objects that were created using
    `Object.create` implemented with this library.

* :warning: Object.getOwnPropertyNames

    This method uses Object.keys, so it will not be accurate on legacy
    engines.

* Object.isSealed

    Returns "false" in all legacy engines for all objects, which is
    conveniently guaranteed to be accurate.

* Object.isFrozen

    Returns "false" in all legacy engines for all objects, which is
    conveniently guaranteed to be accurate.

* Object.isExtensible

    Works like a charm, by trying very hard to extend the object then
    redacting the extension.

### May fail

* :warning: Object.getOwnPropertyDescriptor
    
    The behavior of this shim does not conform to ES5.  It should
    probably not be used at this time, until its behavior has been
    reviewed and been confirmed to be useful in legacy engines.

* :warning: Object.defineProperty

    In the worst of circumstances, IE 8 provides a version of this
    method that only works on DOM objects.  This sham will not be
    installed.  The given version of `defineProperty` will throw an
    exception if used on non-DOM objects.

    In slightly better circumstances, this method will silently fail to
    set "writable", "enumerable", and "configurable" properties.
    
    Providing a getter or setter with "get" or "set" on a descriptor
    will silently fail on engines that lack "__defineGetter__" and
    "__defineSetter__", which include all versions of IE.

    https://github.com/kriskowal/es5-shim/issues#issue/5

* :warning: Object.defineProperties

    This uses the Object.defineProperty shim

* Object.seal

    Silently fails on all legacy engines.  This should be
    fine unless you are depending on the safety and security
    provisions of this method, which you cannot possibly
    obtain in legacy engines.

* Object.freeze

    Silently fails on all legacy engines.  This should be
    fine unless you are depending on the safety and security
    provisions of this method, which you cannot possibly
    obtain in legacy engines.

* Object.preventExtensions

    Silently fails on all legacy engines.  This should be
    fine unless you are depending on the safety and security
    provisions of this method, which you cannot possibly
    obtain in legacy engines.

