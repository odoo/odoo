<a href="https://promisesaplus.com/"><img src="https://promisesaplus.com/assets/logo-small.png" align="right" /></a>
# promise

This is a simple implementation of Promises.  It is a super set of ES6 Promises designed to have readable, performant code and to provide just the extensions that are absolutely necessary for using promises today.

For detailed tutorials on its use, see www.promisejs.org

[![Build Status](https://img.shields.io/travis/then/promise/master.svg)](https://travis-ci.org/then/promise)
[![Dependency Status](https://img.shields.io/gemnasium/then/promise.svg)](https://gemnasium.com/then/promise)
[![NPM version](https://img.shields.io/npm/v/promise.svg)](https://www.npmjs.org/package/promise)

## Installation

**Server:**

    $ npm install promise

**Client:**

You can use browserify on the client, or use the pre-compiled script that acts as a polyfill.

```html
<script src="https://www.promisejs.org/polyfills/promise-6.1.0.js"></script>
```

Note that the [es5-shim](https://github.com/es-shims/es5-shim) must be loaded before this library to support browsers pre IE9.

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/es5-shim/3.4.0/es5-shim.min.js"></script>
```

## Usage

The example below shows how you can load the promise library (in a way that works on both client and server).  It then demonstrates creating a promise from scratch.  You simply call `new Promise(fn)`.  There is a complete specification for what is returned by this method in [Promises/A+](http://promises-aplus.github.com/promises-spec/).

```javascript
var Promise = require('promise');

var promise = new Promise(function (resolve, reject) {
  get('http://www.google.com', function (err, res) {
    if (err) reject(err);
    else resolve(res);
  });
});
```

## API

Before all examples, you will need:

```js
var Promise = require('promise');
```

### new Promise(resolver)

This creates and returns a new promise.  `resolver` must be a function.  The `resolver` function is passed two arguments:

 1. `resolve` should be called with a single argument.  If it is called with a non-promise value then the promise is fulfilled with that value.  If it is called with a promise (A) then the returned promise takes on the state of that new promise (A).
 2. `reject` should be called with a single argument.  The returned promise will be rejected with that argument.

### Static Functions

  These methods are invoked by calling `Promise.methodName`.

#### Promise.resolve(value)

(deprecated aliases: `Promise.from(value)`, `Promise.cast(value)`)

Converts values and foreign promises into Promises/A+ promises.  If you pass it a value then it returns a Promise for that value.  If you pass it something that is close to a promise (such as a jQuery attempt at a promise) it returns a Promise that takes on the state of `value` (rejected or fulfilled).

#### Promise.all(array)

Returns a promise for an array.  If it is called with a single argument that `Array.isArray` then this returns a promise for a copy of that array with any promises replaced by their fulfilled values.  Otherwise it returns a promise for an array that conatins its arguments, except with promises replaced by their resolution values.  e.g.

```js
Promise.all([Promise.resolve('a'), 'b', Promise.resolve('c')])
  .then(function (res) {
    assert(res[0] === 'a')
    assert(res[1] === 'b')
    assert(res[2] === 'c')
  })

Promise.all(Promise.resolve('a'), 'b', Promise.resolve('c'))
  .then(function (res) {
    assert(res[0] === 'a')
    assert(res[1] === 'b')
    assert(res[2] === 'c')
  })
```

#### Promise.denodeify(fn)

_Non Standard_

Takes a function which accepts a node style callback and returns a new function that returns a promise instead.

e.g.

```javascript
var fs = require('fs')

var read = Promise.denodeify(fs.readFile)
var write = Promise.denodeify(fs.writeFile)

var p = read('foo.json', 'utf8')
  .then(function (str) {
    return write('foo.json', JSON.stringify(JSON.parse(str), null, '  '), 'utf8')
  })
```

#### Promise.nodeify(fn)

_Non Standard_

The twin to `denodeify` is useful when you want to export an API that can be used by people who haven't learnt about the brilliance of promises yet.

```javascript
module.exports = Promise.nodeify(awesomeAPI)
function awesomeAPI(a, b) {
  return download(a, b)
}
```

If the last argument passed to `module.exports` is a function, then it will be treated like a node.js callback and not parsed on to the child function, otherwise the API will just return a promise.

### Prototype Methods

These methods are invoked on a promise instance by calling `myPromise.methodName`

### Promise#then(onFulfilled, onRejected)

This method follows the [Promises/A+ spec](http://promises-aplus.github.io/promises-spec/).  It explains things very clearly so I recommend you read it.

Either `onFulfilled` or `onRejected` will be called and they will not be called more than once.  They will be passed a single argument and will always be called asynchronously (in the next turn of the event loop).

If the promise is fulfilled then `onFulfilled` is called.  If the promise is rejected then `onRejected` is called.

The call to `.then` also returns a promise.  If the handler that is called returns a promise, the promise returned by `.then` takes on the state of that returned promise.  If the handler that is called returns a value that is not a promise, the promise returned by `.then` will be fulfilled with that value. If the handler that is called throws an exception then the promise returned by `.then` is rejected with that exception.

#### Promise#catch(onRejected)

Sugar for `Promise#then(null, onRejected)`, to mirror `catch` in synchronous code.

#### Promise#done(onFulfilled, onRejected)

_Non Standard_

The same semantics as `.then` except that it does not return a promise and any exceptions are re-thrown so that they can be logged (crashing the application in non-browser environments)

#### Promise#nodeify(callback)

_Non Standard_

If `callback` is `null` or `undefined` it just returns `this`.  If `callback` is a function it is called with rejection reason as the first argument and result as the second argument (as per the node.js convention).

This lets you write API functions that look like:

```javascript
function awesomeAPI(foo, bar, callback) {
  return internalAPI(foo, bar)
    .then(parseResult)
    .then(null, retryErrors)
    .nodeify(callback)
}
```

People who use typical node.js style callbacks will be able to just pass a callback and get the expected behavior.  The enlightened people can not pass a callback and will get awesome promises.

## Extending Promises

  There are three options for extending the promises created by this library.

### Inheritance

  You can use inheritance if you want to create your own complete promise library with this as your basic starting point, perfect if you have lots of cool features you want to add.  Here is an example of a promise library called `Awesome`, which is built on top of `Promise` correctly.

```javascript
var Promise = require('promise');
function Awesome(fn) {
  if (!(this instanceof Awesome)) return new Awesome(fn);
  Promise.call(this, fn);
}
Awesome.prototype = Object.create(Promise.prototype);
Awesome.prototype.constructor = Awesome;

//Awesome extension
Awesome.prototype.spread = function (cb) {
  return this.then(function (arr) {
    return cb.apply(this, arr);
  })
};
```

  N.B. if you fail to set the prototype and constructor properly or fail to do Promise.call, things can fail in really subtle ways.

### Wrap

  This is the nuclear option, for when you want to start from scratch.  It ensures you won't be impacted by anyone who is extending the prototype (see below).

```javascript
function Uber(fn) {
  if (!(this instanceof Uber)) return new Uber(fn);
  var _prom = new Promise(fn);
  this.then = _prom.then;
}

Uber.prototype.spread = function (cb) {
  return this.then(function (arr) {
    return cb.apply(this, arr);
  })
};
```

### Extending the Prototype

  In general, you should never extend the prototype of this promise implimenation because your extensions could easily conflict with someone elses extensions.  However, this organisation will host a library of extensions which do not conflict with each other, so you can safely enable any of those.  If you think of an extension that we don't provide and you want to write it, submit an issue on this repository and (if I agree) I'll set you up with a repository and give you permission to commit to it.

## License

  MIT
